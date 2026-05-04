# Flutter Wrapper
-keep class io.flutter.app.** { *; }
-keep class io.flutter.plugin.**  { *; }
-keep class io.flutter.util.**  { *; }
-keep class io.flutter.view.**  { *; }
-keep class io.flutter.**  { *; }
-keep class io.flutter.plugins.**  { *; }

# Dio
-keep class dio.** { *; }
-dontwarn dio.**

# Encrypt
-keep class org.spongycastle.** { *; }
-dontwarn org.spongycastle.**

# Firebase
-keep class com.google.firebase.** { *; }
-dontwarn com.google.firebase.**

# Google Fonts
-keep class com.google.android.gms.** { *; }
-dontwarn com.google.android.gms.**

# Local Auth
-keep class androidx.biometric.** { *; }
-dontwarn androidx.biometric.**

# Shared Preferences
-keep class androidx.preference.** { *; }

# Keep model classes
-keep class com.trading1b.trading_app.** { *; }

# Keep serialization
-keepattributes *Annotation*, Signature, InnerClasses, EnclosingMethod
-keepnames class * implements java.io.Serializable
-keepclassmembers class * implements java.io.Serializable {
    static final long serialVersionUID;
    private static final java.io.ObjectStreamField[] serialPersistentFields;
    private void writeObject(java.io.ObjectOutputStream);
    private void readObject(java.io.ObjectInputStream);
    java.lang.Object writeReplace();
    java.lang.Object readResolve();
}
