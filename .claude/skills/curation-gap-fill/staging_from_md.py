#!/usr/bin/env python3
"""Convert a staging markdown file into a WebBench "Load staged instances" JSON file.

The WebBench toolbar's file_upload button ("Load staged instances from a local file")
accepts the JSON its own Export button writes: a UserInstances object

    {"newInstances": [...], "updatedInstances": [], "deletedInstances": [], "bookmarks": []}

This script writes that shape, following the conventions of the WebBench frontend
(reactome/curator-tool-frontend: UserInstancesService.importUserInstancesFromFile,
DataService.hydrateUserInstances, InstanceUtilities.handleInstanceAttributes) and of the
Paper2Path emitter (reactome/curator-tool-llm: curator_llm/services/emitter.py):

  * every NEW instance is its own entry in newInstances, with a negative dbId;
  * references between instances are shells {dbId, displayName, schemaClassName} -
    nothing is nested, and the frontend swaps shells for its cached instances;
  * anything already in gk_central is only ever a shell, never re-emitted;
  * dbId and displayName are repeated inside attributes, as the frontend does for an
    instance a curator creates.

Only NEW instances are written. Existing content is linked (e.g. a new Pathway's
hasEvent lists an existing pathway as a shell, giving it a second parent) but never
edited: updatedInstances would need each instance's full current attribute set, and a
stale copy committed later could overwrite a colleague's edits.

Every class and slot is checked against reactome_domain_model.json (bundled; from
reactome/curator-tool-llm resources/, Apache-2.0), including which slots are lists and
which take instances rather than literals.

Staging markdown format
-----------------------
Free text anywhere outside an instance block is ignored. An instance block is a level-3
heading naming a key and a class, followed by one bullet per slot value:

    ### @rxn-lpl Reaction
    - name: LPL hydrolyses TAG in VLDL to fatty acids and glycerol
    - species: #48887 "Homo sapiens" Species
    - input: @ent-vldl-tag
    - input: #29438 "H2O [extracellular region]" SimpleEntity
    - summation: @sum-lpl
    - literatureReference: @lit-12345678

    ### @sum-lpl Summation
    - text: |
      Lipoprotein lipase (LPL), anchored at the capillary endothelium ...
      continuation lines are indented two spaces.
    - literatureReference: @lit-12345678

    ### @lit-12345678 LiteratureReference
    - pubMedIdentifier: 12345678
    - title: ...
    - year: 2019

Values:
  @key                         another NEW instance in this file
  #<dbId> "<displayName>" Cls  an EXISTING gk_central instance (shell)
  |                            a multi-line literal; following lines indented 2 spaces
  anything else                a literal; ints/booleans are typed from the schema

A list slot takes one bullet per value. A single-valued slot given twice is an error.
displayName may be set explicitly; otherwise it is derived (name[0] plus
" [compartment]" for a PhysicalEntity, the first 60 characters of a Summation's text,
"PMID:<id>" for a LiteratureReference).

Usage:
    python3 staging_from_md.py proposal_staging.md                 # writes user-instances-<ts>.json
    python3 staging_from_md.py proposal_staging.md -o out.json
    python3 staging_from_md.py proposal_staging.md --check          # validate only
    python3 staging_from_md.py proposal_staging.md --first-id -1000 # start new dbIds lower

Stdlib only.
"""
import argparse
import datetime as _dt
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SCHEMA_PATH = os.path.join(HERE, 'reactome_domain_model.json')

PRIMITIVES = {'String', 'Integer', 'Long', 'Boolean', 'Double', 'int', 'byte[]'}
# Physical entity classes get " [compartment]" appended to a derived displayName.
PE_ROOT = 'PhysicalEntity'

HEAD_RE = re.compile(r'^###\s+@([A-Za-z0-9_.:\-]+)\s+([A-Za-z_]+)\s*$')
SLOT_RE = re.compile(r'^-\s+([A-Za-z_][A-Za-z0-9_]*)\s*:\s?(.*)$')
EXISTING_RE = re.compile(r'^#(\d+)\s+"((?:[^"\\]|\\.)*)"\s+([A-Za-z_]+)\s*$')
NEWREF_RE = re.compile(r'^@([A-Za-z0-9_.:\-]+)\s*$')


class StagingError(Exception):
    pass


# ── schema ──────────────────────────────────────────────────────────────────
class Schema:
    def __init__(self, path=SCHEMA_PATH):
        with open(path) as fh:
            data = json.load(fh)
        self.classes = {c['className']: c for c in data['classes']}

    def has(self, cls):
        return cls in self.classes

    def ancestry(self, cls):
        out = []
        while cls and cls in self.classes:
            out.append(cls)
            cls = self.classes[cls].get('extends')
        return out

    def is_a(self, cls, root):
        return root in self.ancestry(cls)

    def slot(self, cls, name):
        """(type, is_collection) for a slot, or None if the class has no such slot."""
        for k in self.ancestry(cls):
            for f in self.classes[k].get('fields', []):
                if f['name'] == name:
                    # Collections record their element type as elementType; a few are graph
                    # relationship wrappers (e.g. hasEvent -> HasEvent) that are not schema
                    # classes - those still take instances, just without a class check.
                    return f.get('type') or f.get('elementType'), bool(f.get('collection'))
        return None


# ── parsing ─────────────────────────────────────────────────────────────────
def parse(text):
    """Return an ordered list of blocks: {key, cls, line, slots: [(name, raw, line)]}."""
    blocks, cur = [], None
    lines = text.splitlines()
    i = 0
    in_fence = False
    while i < len(lines):
        line = lines[i]
        if line.strip().startswith('```'):
            in_fence = not in_fence
            i += 1
            continue
        if in_fence:
            i += 1
            continue
        m = HEAD_RE.match(line)
        if m:
            cur = {'key': m.group(1), 'cls': m.group(2), 'line': i + 1, 'slots': []}
            blocks.append(cur)
            i += 1
            continue
        if line.startswith('#'):          # any other heading ends the current block
            cur = None
            i += 1
            continue
        if cur is not None:
            s = SLOT_RE.match(line)
            if s:
                name, raw = s.group(1), s.group(2).rstrip()
                if raw.strip() == '|':
                    body, j = [], i + 1
                    while j < len(lines) and (lines[j].startswith('  ') or not lines[j].strip()):
                        if not lines[j].strip() and (j + 1 >= len(lines) or not lines[j + 1].startswith('  ')):
                            break
                        body.append(lines[j][2:])
                        j += 1
                    cur['slots'].append((name, ('BLOCK', '\n'.join(body).strip()), i + 1))
                    i = j
                    continue
                cur['slots'].append((name, raw, i + 1))
            elif line.strip() and not line.startswith(' '):
                cur = None                # prose after a block ends it
        i += 1
    return blocks


def _literal(raw, typ, where):
    if isinstance(raw, tuple):            # multi-line block
        return raw[1]
    v = raw.strip()
    if typ in ('Integer', 'Long', 'int'):
        if not re.fullmatch(r'-?\d+', v):
            raise StagingError(f'{where}: expected an integer, got {v!r}')
        return int(v)
    if typ == 'Double':
        return float(v)
    if typ == 'Boolean':
        if v.lower() not in ('true', 'false'):
            raise StagingError(f'{where}: expected true/false, got {v!r}')
        return v.lower() == 'true'
    if len(v) >= 2 and v[0] == v[-1] == '"':
        v = v[1:-1]
    return v


# ── conversion ──────────────────────────────────────────────────────────────
def convert(text, schema, first_id=-1):
    blocks = parse(text)
    if not blocks:
        raise StagingError('no instance blocks found (expected "### @key ClassName" headings)')
    errors, warnings = [], []

    keys = {}
    next_id = first_id
    for b in blocks:
        if b['key'] in keys:
            errors.append(f"line {b['line']}: @{b['key']} defined twice")
            continue
        if not schema.has(b['cls']):
            errors.append(f"line {b['line']}: unknown class {b['cls']}")
        keys[b['key']] = {'dbId': next_id, 'cls': b['cls'], 'block': b}
        next_id -= 1

    used = set()
    insts = {}
    for b in blocks:
        k, cls = b['key'], b['cls']
        if k not in keys or keys[k]['block'] is not b or not schema.has(cls):
            continue
        attrs, explicit_dn = {}, None
        for name, raw, ln in b['slots']:
            where = f'line {ln} (@{k}.{name})'
            if name == 'displayName':
                explicit_dn = _literal(raw, 'String', where)
                continue
            sl = schema.slot(cls, name)
            if sl is None:
                errors.append(f'{where}: {cls} has no slot "{name}"')
                continue
            typ, is_list = sl
            instance_slot = typ not in PRIMITIVES
            val = None
            rv = raw if isinstance(raw, tuple) else raw.strip()
            if not isinstance(rv, tuple) and (m := NEWREF_RE.match(rv)):
                if not instance_slot:
                    errors.append(f'{where}: slot takes a {typ} literal, not an instance reference')
                    continue
                ref = m.group(1)
                if ref not in keys:
                    errors.append(f'{where}: @{ref} is not defined in this file')
                    continue
                used.add(ref)
                val = ('NEW', ref)
            elif not isinstance(rv, tuple) and (m := EXISTING_RE.match(rv)):
                if not instance_slot:
                    errors.append(f'{where}: slot takes a {typ} literal, not an instance reference')
                    continue
                ecls = m.group(3)
                if not schema.has(ecls):
                    errors.append(f'{where}: unknown class {ecls} on existing reference')
                    continue
                if typ and schema.has(typ) and not schema.is_a(ecls, typ):
                    warnings.append(f'{where}: {ecls} is not a {typ} per the schema; check the reference')
                val = {'dbId': int(m.group(1)), 'displayName': m.group(2).replace('\\"', '"'),
                       'schemaClassName': ecls}
            else:
                if instance_slot:
                    errors.append(f'{where}: slot takes a {typ} instance - use @key or #dbId "name" Class, got {rv!r}')
                    continue
                try:
                    val = _literal(raw, typ, where)
                except StagingError as e:
                    errors.append(str(e))
                    continue
            if is_list:
                attrs.setdefault(name, []).append(val)
            elif name in attrs:
                errors.append(f'{where}: {cls}.{name} is single-valued but given more than once')
            else:
                attrs[name] = val
        insts[k] = {'cls': cls, 'attrs': attrs, 'explicit_dn': explicit_dn}

    if errors:
        raise StagingError('\n'.join(errors))

    # displayNames (may depend on referenced instances' displayNames, e.g. compartments)
    dn = {}

    def display(k, stack=()):
        if k in dn:
            return dn[k]
        if k in stack:
            return f'@{k}'
        it = insts[k]
        if it['explicit_dn']:
            dn[k] = it['explicit_dn']
            return dn[k]
        a, cls = it['attrs'], it['cls']
        name = a.get('name')
        name = name[0] if isinstance(name, list) and name else (name or '')
        if cls == 'Summation':
            t = ' '.join(a.get('text', '').split())
            out = t[:60] + ('...' if len(t) > 60 else '')
        elif cls == 'LiteratureReference':
            out = f"PMID:{a['pubMedIdentifier']}" if 'pubMedIdentifier' in a else a.get('title', f'@{k}')
        elif schema.is_a(cls, PE_ROOT) and name:
            comp = a.get('compartment')
            comp = comp[0] if isinstance(comp, list) and comp else comp
            cname = ''
            if isinstance(comp, dict):
                cname = comp['displayName']
            elif isinstance(comp, tuple):
                cname = display(comp[1], stack + (k,))
            out = f'{name} [{cname}]' if cname else name
        else:
            out = name or f'@{k}'
        dn[k] = out
        return out

    for k in insts:
        display(k)

    def shell(v):
        if isinstance(v, tuple):
            r = v[1]
            return {'dbId': keys[r]['dbId'], 'displayName': dn[r], 'schemaClassName': keys[r]['cls']}
        return v

    new_instances = []
    for k, it in insts.items():
        attrs = {}
        for n, v in it['attrs'].items():
            attrs[n] = [shell(x) for x in v] if isinstance(v, list) else shell(v)
        db_id = keys[k]['dbId']
        new_instances.append({
            'dbId': db_id, 'displayName': dn[k], 'schemaClassName': it['cls'],
            'attributes': {'dbId': db_id, 'displayName': dn[k], **attrs}})

    roots = [k for k in insts if k not in used]
    non_event_roots = [k for k in roots if not schema.is_a(insts[k]['cls'], 'Event')]
    if non_event_roots:
        warnings.append('new instances referenced by nothing else in the file (check they are '
                        'meant to stand alone): ' + ', '.join('@' + k for k in non_event_roots))
    payload = {'newInstances': new_instances, 'updatedInstances': [],
               'deletedInstances': [], 'bookmarks': []}
    return payload, warnings, {k: keys[k]['dbId'] for k in insts}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('staging_md')
    ap.add_argument('-o', '--out', help='output JSON path (default user-instances-<timestamp>.json '
                                        'next to the input)')
    ap.add_argument('--first-id', type=int, default=-1,
                    help='dbId for the first new instance (default -1; counts down)')
    ap.add_argument('--check', action='store_true', help='validate only; write nothing')
    ap.add_argument('--schema', default=SCHEMA_PATH)
    a = ap.parse_args(argv)
    if a.first_id >= 0:
        ap.error('--first-id must be negative')

    with open(a.staging_md) as fh:
        text = fh.read()
    try:
        payload, warnings, ids = convert(text, Schema(a.schema), a.first_id)
    except StagingError as e:
        print('STAGING FILE REJECTED:\n' + str(e), file=sys.stderr)
        return 1

    by_cls = {}
    for i in payload['newInstances']:
        by_cls[i['schemaClassName']] = by_cls.get(i['schemaClassName'], 0) + 1
    print(f"{len(payload['newInstances'])} new instances: " +
          ', '.join(f'{n} {c}' for c, n in sorted(by_cls.items())))
    for w in warnings:
        print('WARN', w)
    if a.check:
        print('check only: nothing written')
        return 0
    out = a.out
    if not out:
        ts = _dt.datetime.now(_dt.timezone.utc).strftime('%Y-%m-%dT%H-%M-%S-%f')[:-3] + 'Z'
        out = os.path.join(os.path.dirname(os.path.abspath(a.staging_md)), f'user-instances-{ts}.json')
    if not out.lower().endswith('.json'):
        out += '.json'
    with open(out, 'w') as fh:
        json.dump(payload, fh)
    print('wrote', out)
    print('Load it in WebBench with the file_upload button ("Load staged instances from a local '
          'file"). Loading REPLACES your current staged changes; WebBench backs them up first '
          '(recover with "Restore staged-changes backup").')
    return 0


if __name__ == '__main__':
    sys.exit(main())
