import 'dart:io';
import 'dart:typed_data';
import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';
import 'package:path_provider/path_provider.dart';
import 'package:path/path.dart' as path;
import 'package:google_mlkit_text_recognition/google_mlkit_text_recognition.dart';
import 'dart:ui' as ui;

void main() {
  runApp(MyApp());
}

class MyApp extends StatelessWidget {
  const MyApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      debugShowCheckedModeBanner: false,
      home: TextRecognitionScreen(),
    );
  }
}

class TextRecognitionScreen extends StatefulWidget {
  const TextRecognitionScreen({super.key});

  @override
  _TextRecognitionScreenState createState() => _TextRecognitionScreenState();
}

class _TextRecognitionScreenState extends State<TextRecognitionScreen> {
  File? _imageFile;
  String _extractedText = "No text extracted yet.";
  final ImagePicker _picker = ImagePicker();

  // 이미지 자르기 관련 변수들
  bool _isCropping = false;
  Rect _cropRect = Rect.zero;
  //double _imageWidth = 0;
  //double _imageHeight = 0;
  Offset _startDragOffset = Offset.zero;

  Future<void> _pickImage() async {
    final pickedFile = await _picker.pickImage(source: ImageSource.gallery);
    if (pickedFile != null) {
      final tempDir = await getTemporaryDirectory();
      final tempPath = '${tempDir.path}/temp_image.jpg';
      final tempFile = File(tempPath);
      await File(pickedFile.path).copy(tempPath);

      setState(() {
        _imageFile = tempFile;
        _isCropping = false;
        _cropRect = Rect.zero;
      });
    }
  }

  Future<void> _extractText() async {
    if (_imageFile == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('이미지를 먼저 선택해주세요!')),
      );
      return;
    }

    try {
      final inputImage = InputImage.fromFile(_imageFile!);
      final textRecognizer = TextRecognizer(script: TextRecognitionScript.korean);

      final RecognizedText recognizedText = await textRecognizer.processImage(inputImage);

      setState(() {
        _extractedText = recognizedText.text.isNotEmpty
            ? recognizedText.text
            : "텍스트를 감지하지 못했습니다.";
      });

      textRecognizer.close();
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('텍스트 추출 중 오류가 발생했습니다: $e')),
      );
    }
  }

  Future<void> _saveEditedImage() async {
    if (_imageFile == null) return;

    try {
      final tempDir = await getTemporaryDirectory();
      final uniqueFileName = 'edited_image_${DateTime.now().millisecondsSinceEpoch}.jpg';
      final newImagePath = path.join(tempDir.path, uniqueFileName);

      if (_isCropping && _cropRect != Rect.zero) {
        final Uint8List bytes = await _imageFile!.readAsBytes();
        final ui.Codec codec = await ui.instantiateImageCodec(bytes);
        final ui.FrameInfo frameInfo = await codec.getNextFrame();

        final screenWidth = MediaQuery.of(context).size.width;
        final imageScreenWidth = frameInfo.image.width.toDouble();
        final widthRatio = imageScreenWidth / screenWidth;

        final actualCropRect = Rect.fromLTWH(
          _cropRect.left * widthRatio,
          _cropRect.top * widthRatio,
          _cropRect.width * widthRatio,
          _cropRect.height * widthRatio,
        );

        final ui.PictureRecorder recorder = ui.PictureRecorder();
        final Canvas canvas = Canvas(recorder);
        canvas.drawImageRect(
          frameInfo.image,
          Rect.fromLTWH(
            actualCropRect.left,
            actualCropRect.top,
            actualCropRect.width,
            actualCropRect.height,
          ),
          Rect.fromLTWH(0, 0, actualCropRect.width, actualCropRect.height),
          Paint(),
        );

        final ui.Picture picture = recorder.endRecording();
        final ui.Image croppedImage = await picture.toImage(
          actualCropRect.width.toInt(),
          actualCropRect.height.toInt(),
        );

        final byteData = await croppedImage.toByteData(format: ui.ImageByteFormat.png);
        final croppedBytes = byteData!.buffer.asUint8List();

        final croppedFile = File(newImagePath)..writeAsBytesSync(croppedBytes);

        setState(() {
          _imageFile = croppedFile;
          _isCropping = false;
        });

        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('이미지가 저장되었습니다: $newImagePath')),
        );
      }
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('이미지 저장 중 오류가 발생했습니다: $e')),
      );
    }
  }

  Widget _buildCroppableImage() {
    if (_imageFile == null) return Container();

    return GestureDetector(
      onPanStart: _isCropping ? _onPanStart : null,
      onPanUpdate: _isCropping ? _onPanUpdate : null,
      child: Stack(
        children: [
          Image.file(
            _imageFile!,
            width: double.infinity,
            fit: BoxFit.fitWidth,
          ),
          if (_isCropping)
            CustomPaint(
              painter: CropPainter(_cropRect),
            ),
        ],
      ),
    );
  }

  void _onPanStart(DragStartDetails details) {
    final RenderBox box = context.findRenderObject() as RenderBox;
    final localPosition = box.globalToLocal(details.globalPosition);
    setState(() {
      _startDragOffset = localPosition;
      _cropRect = Rect.fromPoints(_startDragOffset, _startDragOffset);
    });
  }

  void _onPanUpdate(DragUpdateDetails details) {
    final RenderBox box = context.findRenderObject() as RenderBox;
    final localPosition = box.globalToLocal(details.globalPosition);
    setState(() {
      _cropRect = Rect.fromPoints(_startDragOffset, localPosition);
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text('이미지 편집 및 텍스트 추출'),
      ),
      body: SingleChildScrollView(
        child: Column(
          children: [
            if (_imageFile == null)
              Center(
                child: ElevatedButton(
                  onPressed: () => _pickImage(),
                  child: Text('이미지 선택'),
                ),
              )
            else
              Column(
                children: [
                  _buildCroppableImage(),
                  ElevatedButton(
                    onPressed: () {
                      setState(() {
                        _isCropping = !_isCropping;
                      });
                    },
                    child: Text(_isCropping ? '자르기 종료' : '이미지 자르기'),
                  ),
                  ElevatedButton(
                    onPressed: _saveEditedImage,
                    child: Text('편집된 이미지 저장'),
                  ),
                  ElevatedButton(
                    onPressed: _extractText,
                    child: Text('텍스트 추출'),
                  ),
                  Text(_extractedText),
                ],
              ),
          ],
        ),
      ),
    );
  }
}

class CropPainter extends CustomPainter {
  final Rect cropRect;

  CropPainter(this.cropRect);

  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..color = Colors.black.withOpacity(0.5)
      ..style = PaintingStyle.fill;

    canvas.drawPath(
      Path.combine(
        PathOperation.difference,
        Path()..addRect(Rect.fromLTWH(0, 0, size.width, size.height)),
        Path()..addRect(cropRect),
      ),
      paint,
    );

    final borderPaint = Paint()
      ..color = Colors.white
      ..style = PaintingStyle.stroke
      ..strokeWidth = 2.0;

    canvas.drawRect(cropRect, borderPaint);
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => true;
}
