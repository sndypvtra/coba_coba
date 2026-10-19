# ARCore uses reflection for some classes.
-keep class com.google.ar.** { *; }
-keepattributes *Annotation*, InnerClasses
-keep,includedescriptorclasses class id.ukurpaket.app.**$$serializer { *; }
-keepclassmembers class id.ukurpaket.app.** { *** Companion; }
-keepclasseswithmembers class id.ukurpaket.app.** { kotlinx.serialization.KSerializer serializer(...); }
