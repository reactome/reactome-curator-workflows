#!/usr/bin/env python3
"""Install, switch on/off, update and test the Reactome MCP servers.

Two MCP servers, both read-only:

  gk-central  nightly copy of gk_central on the curator server (remote, password)
  ols         EBI Ontology Lookup Service (public, no credentials)

Nothing secret is ever written to the repository, to a Claude config file, or
to this script's output. Passwords live in the macOS Keychain (elsewhere: an
owner-only file under ~/.config/reactome/mcp/secrets/), and the Claude config
files point at a launcher that fetches the password at start-up. Connection
details (host, ports) are private too: they live in
~/.config/reactome/mcp/config.json, never in the repo.

Standard library only. Python 3.9+.

Usage (see SKILL.md for the full walk-through):
  reactome_mcp.py status
  reactome_mcp.py install-server              # mcp-neo4j-cypher + launcher
  reactome_mcp.py install-ols
  reactome_mcp.py configure gk-central --bolt URL --http URL
  reactome_mcp.py set-password gk-central     # run in your own terminal
  reactome_mcp.py enable  <server>            # register with Claude Code + Desktop
  reactome_mcp.py disable <server>            # unregister (any server name)
  reactome_mcp.py test    <server>            # live read-only query
  reactome_mcp.py run <server>                # launcher entry point (used by Claude)
"""

import argparse
import base64
import datetime
import getpass
import hashlib
import json
import os
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

# Pinned so every curator runs the same server; bump deliberately (update-server).
NEO4J_MCP_PACKAGE = "mcp-neo4j-cypher==0.6.0"
OLS_MCP_PACKAGE = ("git+https://github.com/seandavi/ols-mcp-server"
                   "@4f22ed75ac271abfb0527ad53119c555d4809bf1")

KEYCHAIN_SERVICE = "reactome-mcp"

HOME = Path.home()
STATE_DIR = HOME / ".config" / "reactome" / "mcp"
CONFIG_PATH = STATE_DIR / "config.json"
SECRETS_DIR = STATE_DIR / "secrets"
LAUNCHER_PATH = STATE_DIR / "reactome_mcp.py"

DEFAULTS = {
    # No host/port defaults for gk-central on purpose: the repo is public.
    "gk-central": {"kind": "neo4j", "auth": "password", "username": "neo4j",
                   "database": "graph.db", "read_timeout": 60},
    "ols": {"kind": "ols"},
}
SERVERS = tuple(DEFAULTS)
IS_MAC = sys.platform == "darwin"
IS_WIN = os.name == "nt"


# ── helpers ─────────────────────────────────────────────────────────────────

def die(msg, code=1):
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(code)


def load_config():
    cfg = {name: dict(d) for name, d in DEFAULTS.items()}
    if CONFIG_PATH.exists():
        for name, values in json.loads(CONFIG_PATH.read_text()).items():
            cfg.setdefault(name, {}).update(values)
    return cfg


def save_config(cfg):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    # Store only what differs from the defaults, so a later default change applies.
    out = {}
    for name, values in cfg.items():
        diff = {k: v for k, v in values.items() if DEFAULTS.get(name, {}).get(k) != v}
        if diff:
            out[name] = diff
    write_private(CONFIG_PATH, json.dumps(out, indent=2) + "\n")


def write_private(path, text):
    """Write a file readable only by the current user (atomic replace)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    fd = os.open(str(tmp), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as fh:
        fh.write(text)
    os.replace(tmp, path)
    if not IS_WIN:
        os.chmod(path, 0o600)


def uv_bin_dir():
    return HOME / ".local" / "bin"


def find_tool(name):
    exe = name + (".exe" if IS_WIN else "")
    local = uv_bin_dir() / exe
    if local.exists():
        return str(local)
    return shutil.which(name)


def run_quiet(cmd):
    try:
        return subprocess.run(cmd, capture_output=True, text=True)
    except FileNotFoundError:
        return None


def file_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def need_server(name):
    if name not in SERVERS:
        die(f"unknown server '{name}' (choose from: {', '.join(SERVERS)})")


# ── secrets ─────────────────────────────────────────────────────────────────

def secret_file(name):
    return SECRETS_DIR / name


def has_secret(name):
    if IS_MAC:
        r = run_quiet(["security", "find-generic-password",
                       "-s", KEYCHAIN_SERVICE, "-a", name])
        return bool(r) and r.returncode == 0
    return secret_file(name).exists()


def get_secret(name):
    if IS_MAC:
        r = run_quiet(["security", "find-generic-password",
                       "-s", KEYCHAIN_SERVICE, "-a", name, "-w"])
        if r and r.returncode == 0:
            return r.stdout.rstrip("\n")
        return None
    path = secret_file(name)
    return path.read_text().rstrip("\n") if path.exists() else None


def cmd_set_password(args):
    need_server(args.server)
    if load_config()[args.server].get("auth") != "password":
        die(f"{args.server} does not use a password")
    if not sys.stdin.isatty():
        die("set-password must be run by you in your own terminal window, "
            "not through Claude, so the password never enters a chat transcript.")
    if IS_MAC:
        # `security` prompts for the value itself: it never passes through this
        # script, the process list, or shell history. -U replaces an old value.
        print(f"Storing the {args.server} password in your login Keychain "
              f"(service '{KEYCHAIN_SERVICE}', account '{args.server}').")
        r = subprocess.run(["security", "add-generic-password", "-U",
                            "-s", KEYCHAIN_SERVICE, "-a", args.server,
                            "-l", f"Reactome MCP ({args.server})", "-w"])
        if r.returncode != 0:
            die("Keychain did not store the password")
    else:
        first = getpass.getpass(f"{args.server} password: ")
        if not first or getpass.getpass("Again: ") != first:
            die("passwords were empty or did not match; nothing stored")
        write_private(secret_file(args.server), first + "\n")
        print(f"Stored in {secret_file(args.server)} (readable only by you).")
    print("Done. Nothing was printed or logged. Run `test` next.")


# ── status ──────────────────────────────────────────────────────────────────

def desktop_config_path():
    if IS_MAC:
        return HOME / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"
    if IS_WIN:
        return Path(os.environ.get("APPDATA", HOME)) / "Claude" / "claude_desktop_config.json"
    return HOME / ".config" / "Claude" / "claude_desktop_config.json"


def read_desktop_config():
    path = desktop_config_path()
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError as e:
        die(f"{path} is not valid JSON ({e}); fix it by hand before continuing")


def plaintext_secret_entries(servers):
    """Names of MCP entries that carry a password inline in their config."""
    flagged = []
    for name, entry in (servers or {}).items():
        blob = json.dumps(entry.get("env", {})) + " " + " ".join(entry.get("args", []))
        if "PASSWORD" in blob.upper():
            flagged.append(name)
    return flagged


def claude_code_servers():
    """{name: raw json} for user-scope servers, read from ~/.claude.json."""
    path = HOME / ".claude.json"
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text()).get("mcpServers", {}) or {}
    except (json.JSONDecodeError, OSError):
        return {}


def cmd_status(_args):
    cfg = load_config()
    print(f"State directory : {STATE_DIR}")
    launcher_ok = LAUNCHER_PATH.exists()
    stale = launcher_ok and file_hash(LAUNCHER_PATH) != file_hash(__file__)
    print(f"Launcher        : {'installed' if launcher_ok else 'NOT installed'}"
          f"{'  (out of date — run install-server)' if stale else ''}")
    for tool in ("uv", "mcp-neo4j-cypher", "ols-mcp-server", "claude"):
        print(f"  {tool:<17}: {find_tool(tool) or 'not found'}")

    desk = read_desktop_config().get("mcpServers", {}) or {}
    code = claude_code_servers()
    print()
    for name in SERVERS:
        c = cfg[name]
        print(f"[{name}]")
        if c.get("kind") == "neo4j":
            print(f"  configured      : {'yes' if c.get('bolt') else 'NO — run configure'}")
        if c.get("auth") == "password":
            print(f"  password stored : {'yes' if has_secret(name) else 'NO — run set-password'}")
        print(f"  Claude Code     : {'registered' if name in code else 'not registered'}")
        print(f"  Claude Desktop  : {'registered' if name in desk else 'not registered'}")

    others = sorted(set(desk) - set(SERVERS))
    if others:
        print(f"\nOther Claude Desktop MCP servers: {', '.join(others)}")
    leaks = plaintext_secret_entries(desk) + plaintext_secret_entries(code)
    if leaks:
        print(f"\nWARNING: a password is written in plain text in these Claude config "
              f"entries: {', '.join(sorted(set(leaks)))}.\n  For gk-central, `enable gk-central` "
              f"replaces the entry with the Keychain launcher; `disable <name>` removes any entry.")


# ── install / update ────────────────────────────────────────────────────────

def install_launcher():
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(__file__, LAUNCHER_PATH)
    if not IS_WIN:
        os.chmod(LAUNCHER_PATH, 0o700)
    print(f"Launcher copied to {LAUNCHER_PATH}")


def uv_install(package, force=False):
    uv = find_tool("uv")
    if not uv:
        die("uv is not installed — see the Prerequisites section of SKILL.md")
    cmd = [uv, "tool", "install", package]
    if force:
        cmd.insert(3, "--force")
    print("$ " + " ".join(cmd))
    if subprocess.run(cmd).returncode != 0:
        die(f"uv could not install {package}")


def cmd_install_server(args):
    uv_install(NEO4J_MCP_PACKAGE, force=args.force)
    install_launcher()
    print("Next: `configure gk-central`, `set-password gk-central`, then `enable gk-central`.")


def cmd_install_ols(args):
    uv_install(OLS_MCP_PACKAGE, force=args.force)
    print("Next: `enable ols`.")


def cmd_update_server(_args):
    uv_install(NEO4J_MCP_PACKAGE, force=True)
    if find_tool("ols-mcp-server"):
        uv_install(OLS_MCP_PACKAGE, force=True)
    install_launcher()
    print("Restart Claude Code / fully quit and reopen Claude Desktop to pick this up.")


def cmd_configure(args):
    need_server(args.server)
    cfg = load_config()
    c = cfg[args.server]
    if c.get("kind") != "neo4j":
        die(f"{args.server} has nothing to configure")
    for key in ("bolt", "http", "username", "database"):
        value = getattr(args, key, None)
        if value:
            c[key] = value.rstrip("/") if key == "http" else value
    if args.read_timeout:
        c["read_timeout"] = args.read_timeout
    if not c.get("bolt") or not c.get("http"):
        die("both --bolt and --http are needed (see the connection card)")
    save_config(cfg)
    print(f"Saved {args.server} connection details to {CONFIG_PATH} (owner-only).")


# ── Claude registration (the on/off switch) ─────────────────────────────────

def launch_spec(name):
    if name == "ols":
        exe = find_tool("ols-mcp-server")
        if not exe:
            die("ols-mcp-server is not installed — run install-ols first")
        return exe, []
    if not LAUNCHER_PATH.exists():
        die("launcher not installed — run install-server first")
    python = sys.executable
    # The Command Line Tools path moves between Xcode updates; the shim doesn't.
    if IS_MAC and python.startswith("/Library/Developer/") and Path("/usr/bin/python3").exists():
        python = "/usr/bin/python3"
    return python, [str(LAUNCHER_PATH), "run", name]


def cmd_enable(args):
    need_server(args.server)
    cfg = load_config()
    c = cfg[args.server]
    if c.get("kind") == "neo4j" and not c.get("bolt"):
        die(f"{args.server} is not configured yet")
    if c.get("auth") == "password" and not has_secret(args.server):
        die(f"no password stored for {args.server} — run set-password first")
    command, cargs = launch_spec(args.server)
    if not args.desktop_only:
        register_code(args.server, command, cargs)
    if not args.code_only:
        register_desktop(args.server, command, cargs)


def cmd_disable(args):
    if not args.desktop_only:
        claude = find_tool("claude")
        if claude:
            r = run_quiet([claude, "mcp", "remove", "--scope", "user", args.server])
            print(f"Claude Code : {'removed' if r and r.returncode == 0 else 'was not registered'}")
    if not args.code_only:
        data = read_desktop_config()
        if args.server in (data.get("mcpServers") or {}):
            backup_desktop()
            del data["mcpServers"][args.server]
            write_desktop(data)
            print("Claude Desktop: removed (fully quit and reopen Desktop)")
        else:
            print("Claude Desktop: was not registered")


def register_code(name, command, cargs):
    claude = find_tool("claude")
    if not claude:
        print("Claude Code : `claude` not found — skipped. Register later with:\n"
              f"  claude mcp add --scope user {name} -- {command} {' '.join(cargs)}")
        return
    # --scope user writes ~/.claude.json. Never --scope project: that writes a
    # .mcp.json into the repo.
    run_quiet([claude, "mcp", "remove", "--scope", "user", name])
    r = run_quiet([claude, "mcp", "add", "--scope", "user", name, "--", command, *cargs])
    if r is None or r.returncode != 0:
        die(f"claude mcp add failed: {(r.stderr or r.stdout).strip() if r else ''}")
    print("Claude Code : registered (user scope; new sessions pick it up)")


def backup_desktop():
    path = desktop_config_path()
    if not path.exists():
        return
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    backup = path.with_name(path.name + f".bak-{stamp}")
    write_private(backup, path.read_text())
    if plaintext_secret_entries(read_desktop_config().get("mcpServers")):
        print(f"Note: backup {backup.name} still contains a plain-text password. "
              f"Delete it once the new setup works.")


def write_desktop(data):
    path = desktop_config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, indent=2) + "\n")
    os.replace(tmp, path)


def register_desktop(name, command, cargs):
    path = desktop_config_path()
    if not path.parent.exists():
        print("Claude Desktop: not installed — skipped")
        return
    data = read_desktop_config()
    backup_desktop()
    # Merge — never replace the file: it also holds Desktop's own preferences.
    data.setdefault("mcpServers", {})[name] = {"command": command, "args": cargs}
    write_desktop(data)
    print("Claude Desktop: registered (fully quit and reopen Desktop)")


# ── launcher ────────────────────────────────────────────────────────────────

def cmd_run(args):
    """Started by Claude Code / Desktop. stdout belongs to the MCP protocol:
    diagnostics go to stderr only, and never include the password."""
    need_server(args.server)
    c = load_config()[args.server]
    exe = find_tool("mcp-neo4j-cypher")
    if not exe:
        die("mcp-neo4j-cypher not installed — run install-server")
    if not c.get("bolt"):
        die(f"{args.server} is not configured — run configure")
    password = get_secret(args.server)
    if not password:
        die(f"no stored password for {args.server} — run set-password")
    env = dict(os.environ)
    env.update({
        "NEO4J_URI": c["bolt"],
        "NEO4J_USERNAME": c.get("username", "neo4j"),
        "NEO4J_PASSWORD": password,
        "NEO4J_DATABASE": c.get("database", "graph.db"),
        "NEO4J_READ_TIMEOUT": str(c.get("read_timeout", 30)),
        "NEO4J_READ_ONLY": "true",
    })
    # --read-only removes write_neo4j_cypher entirely. Non-negotiable: gk_central
    # reports read-write access server-side, so this is the real protection.
    cmd = [exe, "--read-only"]
    if IS_WIN:
        sys.exit(subprocess.run(cmd, env=env).returncode)
    os.execve(exe, cmd, env)


# ── live test ───────────────────────────────────────────────────────────────

def cypher(c, statement, password):
    url = f"{c['http']}/db/{c.get('database', 'graph.db')}/tx/commit"
    body = json.dumps({"statements": [{"statement": statement}]}).encode()
    req = urllib.request.Request(url, data=body, method="POST", headers={
        "Content-Type": "application/json", "Accept": "application/json"})
    if password is not None:
        token = base64.b64encode(f"{c.get('username', 'neo4j')}:{password}".encode()).decode()
        req.add_header("Authorization", "Basic " + token)
    with urllib.request.urlopen(req, timeout=30) as resp:
        payload = json.loads(resp.read())
    if payload.get("errors"):
        raise RuntimeError(payload["errors"][0].get("message", "query failed"))
    rows = payload["results"][0]["data"]
    return [r["row"] for r in rows]


def cmd_test(args):
    need_server(args.server)
    if args.server == "ols":
        try:
            with urllib.request.urlopen("https://www.ebi.ac.uk/ols4/api/ontologies/go", timeout=30) as r:
                print(f"OLS reachable (HTTP {r.status}).")
        except (urllib.error.URLError, OSError) as e:
            die(f"cannot reach EBI OLS: {e}")
        return
    c = load_config()[args.server]
    if not c.get("http"):
        die(f"{args.server} is not configured — run configure")
    password = None
    if c.get("auth") == "password":
        password = get_secret(args.server)
        if not password:
            die(f"no stored password for {args.server} — run set-password")
    try:
        n = cypher(c, "MATCH (p:Pathway) RETURN count(p)", password)[0][0]
    except urllib.error.HTTPError as e:
        if e.code == 401:
            die("authentication failed — the password may have been rotated. "
                "Ask your Reactome contact, then run set-password again.")
        die(f"HTTP {e.code} from {c['http']}")
    except (urllib.error.URLError, OSError) as e:
        die(f"cannot reach {c['http']} ({getattr(e, 'reason', e)}). "
            "Check the http URL and port on the connection card.")
    except RuntimeError as e:
        die(str(e))
    print(f"{args.server}: connected. Pathway count = {n}.")
    try:
        # The copy is refreshed nightly; the newest edit shows whether that ran.
        latest = cypher(c, "MATCH (ie:InstanceEdit) RETURN max(ie.dateTime)", password)
        if latest and latest[0][0]:
            print(f"  Newest edit in copy: {latest[0][0]} (refreshed nightly)")
    except (urllib.error.URLError, OSError, RuntimeError):
        pass
    try:
        # Exact-name match: a prefix match with LIMIT can stop before this name.
        apoc = cypher(c, "SHOW PROCEDURES YIELD name WHERE name = 'apoc.meta.schema' "
                         "RETURN count(*)", password)[0][0]
        print("  APOC schema procedure: " + ("present" if apoc else
              "MISSING — get_neo4j_schema will fail; read queries still work"))
    except (urllib.error.URLError, OSError, RuntimeError) as e:
        print(f"  APOC check could not run: {e}")


# ── CLI ─────────────────────────────────────────────────────────────────────

def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("status").set_defaults(fn=cmd_status)
    for name, fn in (("install-server", cmd_install_server), ("install-ols", cmd_install_ols)):
        s = sub.add_parser(name)
        s.add_argument("--force", action="store_true", help="reinstall over an existing copy")
        s.set_defaults(fn=fn)
    sub.add_parser("update-server").set_defaults(fn=cmd_update_server)

    s = sub.add_parser("configure")
    s.add_argument("server")
    s.add_argument("--bolt", help="bolt:// URL from the connection card")
    s.add_argument("--http", help="http:// URL of the Neo4j Browser port")
    s.add_argument("--username")
    s.add_argument("--database")
    s.add_argument("--read-timeout", dest="read_timeout", type=int)
    s.set_defaults(fn=cmd_configure)

    for name, fn in (("set-password", cmd_set_password), ("test", cmd_test), ("run", cmd_run)):
        s = sub.add_parser(name)
        s.add_argument("server")
        s.set_defaults(fn=fn)

    for name, fn in (("enable", cmd_enable), ("disable", cmd_disable)):
        s = sub.add_parser(name)
        s.add_argument("server")
        g = s.add_mutually_exclusive_group()
        g.add_argument("--code-only", action="store_true")
        g.add_argument("--desktop-only", action="store_true")
        s.set_defaults(fn=fn)

    args = p.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
