package com.example.mpox_detection_submit

import android.Manifest
import android.content.pm.PackageManager
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.os.Bundle
import android.util.Log
import android.view.Surface
import android.widget.Button
import android.widget.ImageView
import android.widget.TextView
import android.widget.Toast
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import androidx.camera.core.*
import androidx.camera.lifecycle.ProcessCameraProvider
import androidx.camera.view.PreviewView
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat
import org.tensorflow.lite.Interpreter
import java.io.File
import java.io.FileInputStream
import java.io.IOException
import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.nio.MappedByteBuffer
import java.nio.channels.FileChannel
import java.util.concurrent.ExecutorService
import java.util.concurrent.Executors

class MainActivity : AppCompatActivity() {

    private lateinit var previewView: PreviewView
    private lateinit var resultText: TextView
    private lateinit var captureButton: Button
    private lateinit var uploadButton: Button
    private lateinit var uploadedImageView: ImageView
    private var imageCapture: ImageCapture? = null
    private lateinit var tflite: Interpreter
    private lateinit var cameraExecutor: ExecutorService

    private val imageSize = 224
    private val cameraPermissionCode = 1001

    // 갤러리에서 이미지 선택 결과 처리
    private val pickImageLauncher = registerForActivityResult(ActivityResultContracts.GetContent()) { uri ->
        uri?.let {
            try {
                val inputStream = contentResolver.openInputStream(it)
                val bitmap = BitmapFactory.decodeStream(inputStream)
                uploadedImageView.setImageBitmap(bitmap)
                val resizedBitmap = Bitmap.createScaledBitmap(bitmap, imageSize, imageSize, false)
                classifyImage(resizedBitmap)
            } catch (e: Exception) {
                resultText.text = "이미지 로딩 실패: ${e.message}"
            }
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        previewView = findViewById(R.id.cameraPreviewView)
        resultText = findViewById(R.id.resultTextView)
        captureButton = findViewById(R.id.captureButton)
        uploadButton = findViewById(R.id.uploadButton)
        uploadedImageView = findViewById(R.id.uploadedImageView)

        cameraExecutor = Executors.newSingleThreadExecutor()

        // 카메라 권한 요청
        if (ContextCompat.checkSelfPermission(this, Manifest.permission.CAMERA)
            == PackageManager.PERMISSION_GRANTED) {
            startCamera()
        } else {
            ActivityCompat.requestPermissions(this, arrayOf(Manifest.permission.CAMERA), cameraPermissionCode)
        }

        // 모델 로드
        try {
            tflite = Interpreter(loadModelFile("model_v2.tflite"))
        } catch (e: Exception) {
            e.printStackTrace()
            resultText.text = "모델 로딩 실패: ${e.message}"
        }

        captureButton.setOnClickListener {
            takePhoto()
        }

        uploadButton.setOnClickListener {
            pickImageLauncher.launch("image/*")
        }
    }

    private fun startCamera() {
        val cameraProviderFuture = ProcessCameraProvider.getInstance(this)

        cameraProviderFuture.addListener({
            val cameraProvider = cameraProviderFuture.get()

            val preview = Preview.Builder()
                .setTargetRotation(Surface.ROTATION_0)
                .build()
                .also {
                    it.setSurfaceProvider(previewView.surfaceProvider)
                }

            imageCapture = ImageCapture.Builder()
                .setTargetRotation(Surface.ROTATION_0)
                .build()

            val cameraSelector = CameraSelector.DEFAULT_BACK_CAMERA

            try {
                cameraProvider.unbindAll()
                cameraProvider.bindToLifecycle(this, cameraSelector, preview, imageCapture)
            } catch (e: Exception) {
                Log.e("CameraX", "카메라 바인딩 실패: ${e.message}")
            }

        }, ContextCompat.getMainExecutor(this))
    }

    private fun takePhoto() {
        val photoFile = File(getExternalFilesDir(null), "captured.jpg")

        val outputOptions = ImageCapture.OutputFileOptions.Builder(photoFile).build()

        imageCapture?.takePicture(
            outputOptions,
            ContextCompat.getMainExecutor(this),
            object : ImageCapture.OnImageSavedCallback {
                override fun onImageSaved(outputFileResults: ImageCapture.OutputFileResults) {
                    val bitmap = BitmapFactory.decodeFile(photoFile.absolutePath)
                    if (bitmap != null) {
                        uploadedImageView.setImageBitmap(bitmap)
                        val resizedBitmap = Bitmap.createScaledBitmap(bitmap, imageSize, imageSize, false)
                        classifyImage(resizedBitmap)
                    } else {
                        resultText.text = "비트맵 변환 실패"
                    }
                }

                override fun onError(exception: ImageCaptureException) {
                    resultText.text = "촬영 실패: ${exception.message}"
                }
            }
        )
    }

    private fun classifyImage(bitmap: Bitmap) {
        val inputBuffer = convertBitmapToByteBuffer(bitmap)

        val output1 = Array(1) { FloatArray(1) }
        val output2 = Array(1) { FloatArray(1) }
        val output3 = Array(1) { FloatArray(1) }

        tflite.run(inputBuffer, output1)
        tflite.run(inputBuffer, output2)
        tflite.run(inputBuffer, output3)

        val predictions = listOf(output1[0][0], output2[0][0], output3[0][0])
        val isMpox = predictions.count { it > 0.5 } > 1

        displayResult(isMpox)
    }

    private fun displayResult(isMpox: Boolean) {
        resultText.text = if (isMpox) {
            "결과: 엠폭스가 의심됩니다. 가까운 의료기관을 방문하세요."
        } else {
            "결과: 엠폭스가 의심되지 않습니다. 증상이 지속되면 전문가의 상담을 받아보세요."
        }
    }

    private fun convertBitmapToByteBuffer(bitmap: Bitmap): ByteBuffer {
        val byteBuffer = ByteBuffer.allocateDirect(4 * imageSize * imageSize * 3)
        byteBuffer.order(ByteOrder.nativeOrder())

        val pixels = IntArray(imageSize * imageSize)
        bitmap.getPixels(pixels, 0, imageSize, 0, 0, imageSize, imageSize)

        for (pixel in pixels) {
            byteBuffer.putFloat(((pixel shr 16) and 0xFF) / 255.0f)
            byteBuffer.putFloat(((pixel shr 8) and 0xFF) / 255.0f)
            byteBuffer.putFloat((pixel and 0xFF) / 255.0f)
        }

        return byteBuffer
    }

    @Throws(IOException::class)
    private fun loadModelFile(modelFileName: String): MappedByteBuffer {
        val fileDescriptor = assets.openFd(modelFileName)
        val inputStream = FileInputStream(fileDescriptor.fileDescriptor)
        val fileChannel = inputStream.channel
        val startOffset = fileDescriptor.startOffset
        val declaredLength = fileDescriptor.declaredLength
        return fileChannel.map(FileChannel.MapMode.READ_ONLY, startOffset, declaredLength)
    }

    override fun onDestroy() {
        super.onDestroy()
        cameraExecutor.shutdown()
    }
}
