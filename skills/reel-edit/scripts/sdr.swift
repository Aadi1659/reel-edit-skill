import AVFoundation
let args = CommandLine.arguments
let src = URL(fileURLWithPath: args[1]); let dst = URL(fileURLWithPath: args[2])
try? FileManager.default.removeItem(at: dst)
let asset = AVURLAsset(url: src)
let comp = AVMutableVideoComposition(propertiesOf: asset)
comp.colorPrimaries = AVVideoColorPrimaries_ITU_R_709_2
comp.colorTransferFunction = AVVideoTransferFunction_ITU_R_709_2
comp.colorYCbCrMatrix = AVVideoYCbCrMatrix_ITU_R_709_2
guard let ex = AVAssetExportSession(asset: asset, presetName: AVAssetExportPresetHighestQuality) else { print("no session"); exit(1) }
ex.videoComposition = comp
ex.outputURL = dst; ex.outputFileType = .mov
let sem = DispatchSemaphore(value: 0)
ex.exportAsynchronously { sem.signal() }
sem.wait()
print(ex.status.rawValue, ex.error?.localizedDescription ?? "ok")
