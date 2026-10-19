plugins {
    id("com.android.application")
}

android {
    namespace = "org.meetiq.offline"
    compileSdk = 35

    defaultConfig {
        applicationId = "org.meetiq.offline"
        minSdk = 26
        targetSdk = 35
        versionCode = 9
        versionName = "0.7.1-prototype"
        ndk { abiFilters += listOf("arm64-v8a", "x86_64") }
        
        externalNativeBuild {
            cmake {
                cppFlags += ""
            }
        }
    }

    buildTypes {
        release {
            isMinifyEnabled = false
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro"
            )
        }
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_1_8
        targetCompatibility = JavaVersion.VERSION_1_8
    }
    sourceSets.getByName("main").jniLibs.srcDir("../vendor/sherpa-onnx/jniLibs")
    packaging {
        jniLibs {
            // CMake and the runtime directory both supply this pinned library.
            pickFirsts += setOf("lib/**/libsherpa-onnx-c-api.so")
        }
    }
    
    externalNativeBuild {
        cmake {
            path = file("src/main/cpp/CMakeLists.txt")
        }
    }
}

dependencies {
    // Add any dependencies here if needed in the future
}
