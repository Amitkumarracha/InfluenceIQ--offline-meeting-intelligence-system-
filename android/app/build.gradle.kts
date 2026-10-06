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
        versionCode = 3
        versionName = "0.3.1-prototype"
        
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
    
    externalNativeBuild {
        cmake {
            path = file("src/main/cpp/CMakeLists.txt")
        }
    }
}

dependencies {
    // Add any dependencies here if needed in the future
}
