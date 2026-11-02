"""macOS Vision helpers: OCR and subject cut-out (no cloud, no model download)."""
import Quartz
import Vision
from Foundation import NSURL
from PIL import Image


def _cgimage(path):
    src = Quartz.CGImageSourceCreateWithURL(NSURL.fileURLWithPath_(str(path)), None)
    return Quartz.CGImageSourceCreateImageAtIndex(src, 0, None)


def ocr(path, langs=("fr-FR",)):
    """Return [{text, conf, bbox:[x0,y0,x1,y1] normalised, top-left origin}]."""
    req = Vision.VNRecognizeTextRequest.alloc().init()
    req.setRecognitionLevel_(Vision.VNRequestTextRecognitionLevelAccurate)
    req.setRecognitionLanguages_(list(langs))
    req.setUsesLanguageCorrection_(False)
    handler = Vision.VNImageRequestHandler.alloc().initWithCGImage_options_(_cgimage(path), None)
    handler.performRequests_error_([req], None)
    out = []
    for r in req.results() or []:
        c = r.topCandidates_(1)[0]
        b = r.boundingBox()
        x, y, w, h = b.origin.x, b.origin.y, b.size.width, b.size.height
        out.append(dict(text=str(c.string()), conf=float(c.confidence()), bbox=[x, 1 - y - h, x + w, 1 - y]))
    return out


def cutout(path, dst):
    """Lift the foreground subject(s) of an image into a transparent PNG. Returns (w, h) or None."""
    req = Vision.VNGenerateForegroundInstanceMaskRequest.alloc().init()
    handler = Vision.VNImageRequestHandler.alloc().initWithCGImage_options_(_cgimage(path), None)
    ok = handler.performRequests_error_([req], None)
    res = req.results()
    if not res:
        return None
    obs = res[0]
    buf, err = obs.generateMaskedImageOfInstances_fromRequestHandler_croppedToInstancesExtent_error_(
        obs.allInstances(), handler, True, None)
    if buf is None:
        return None
    ci = Quartz.CIImage.imageWithCVPixelBuffer_(buf)
    ctx = Quartz.CIContext.contextWithOptions_(None)
    cg = ctx.createCGImage_fromRect_(ci, ci.extent())
    url = NSURL.fileURLWithPath_(str(dst))
    d = Quartz.CGImageDestinationCreateWithURL(url, "public.png", 1, None)
    Quartz.CGImageDestinationAddImage(d, cg, None)
    Quartz.CGImageDestinationFinalize(d)
    im = Image.open(dst)
    return im.size
