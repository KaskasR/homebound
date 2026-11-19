// Renders the Homebound icon to a 1024x1024 PNG: swift scripts/make-icon.swift out.png
import AppKit

let px = 1024
let rep = NSBitmapImageRep(bitmapDataPlanes: nil, pixelsWide: px, pixelsHigh: px, bitsPerSample: 8,
                           samplesPerPixel: 4, hasAlpha: true, isPlanar: false,
                           colorSpaceName: .deviceRGB, bytesPerRow: 0, bitsPerPixel: 0)!
NSGraphicsContext.saveGraphicsState()
NSGraphicsContext.current = NSGraphicsContext(bitmapImageRep: rep)
let inset: CGFloat = 100, side = CGFloat(px) - 2 * inset
let tile = NSBezierPath(roundedRect: NSRect(x: inset, y: inset, width: side, height: side), xRadius: 185, yRadius: 185)
NSGradient(starting: NSColor(srgbRed: 0.33, green: 0.56, blue: 1.0, alpha: 1),
           ending: NSColor(srgbRed: 0.13, green: 0.30, blue: 0.75, alpha: 1))!.draw(in: tile, angle: -90)
let glyph = "🏠" as NSString
let attrs: [NSAttributedString.Key: Any] = [.font: NSFont.systemFont(ofSize: 500)]
let sz = glyph.size(withAttributes: attrs)
glyph.draw(at: NSPoint(x: (CGFloat(px) - sz.width) / 2, y: (CGFloat(px) - sz.height) / 2 + 10), withAttributes: attrs)
NSGraphicsContext.restoreGraphicsState()
try! rep.representation(using: .png, properties: [:])!.write(to: URL(fileURLWithPath: CommandLine.arguments[1]))
