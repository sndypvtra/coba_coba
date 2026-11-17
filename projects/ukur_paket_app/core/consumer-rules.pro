# kept in every app that uses the engine: serialized records and ONNX Runtime's natively created classes
-keepattributes *Annotation*, InnerClasses
-keep,includedescriptorclasses class id.ukurpaket.app.**$$serializer { *; }
-keepclassmembers class id.ukurpaket.app.** { *** Companion; }
-keepclasseswithmembers class id.ukurpaket.app.** { kotlinx.serialization.KSerializer serializer(...); }
-keep class ai.onnxruntime.** { *; }
