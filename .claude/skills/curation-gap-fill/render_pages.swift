import PDFKit
import AppKit
// usage: render_pages <pdf> <outdir> <scale> [pages...]  (1-based)
let a = CommandLine.arguments
let doc = PDFDocument(url: URL(fileURLWithPath: a[1]))!
let out = a[2]; let scale = CGFloat(Double(a[3])!)
let pages = a.count > 4 ? a[4...].map { Int($0)! } : Array(1...doc.pageCount)
for n in pages {
  guard let p = doc.page(at: n-1) else { continue }
  let r = p.bounds(for: .mediaBox)
  let w = Int(r.width*scale), h = Int(r.height*scale)
  let rep = NSBitmapImageRep(bitmapDataPlanes: nil, pixelsWide: w, pixelsHigh: h, bitsPerSample: 8, samplesPerPixel: 4, hasAlpha: true, isPlanar: false, colorSpaceName: .deviceRGB, bytesPerRow: 0, bitsPerPixel: 0)!
  NSGraphicsContext.saveGraphicsState()
  let ctx = NSGraphicsContext(bitmapImageRep: rep)!; NSGraphicsContext.current = ctx
  NSColor.white.setFill(); NSRect(x:0,y:0,width:w,height:h).fill()
  ctx.cgContext.scaleBy(x: scale, y: scale)
  p.draw(with: .mediaBox, to: ctx.cgContext)
  NSGraphicsContext.restoreGraphicsState()
  try! rep.representation(using: .png, properties: [:])!.write(to: URL(fileURLWithPath: "\(out)/page\(n).png"))
  print("\(out)/page\(n).png \(w)x\(h)")
}
