# Downloads and installs the Android SDK depending on supplied platform: darwin or linux

# We must provide a platform (darwin or linux) and we need JAVA_HOME defined
ifdef target_os
    $(info Targeting platform: $(target_os))
else
    $(error target_os is not set)
endif

# Those android NDK/SDK variables can be override when running the file
ifndef ANDROID_NDK_VERSION
    ANDROID_NDK_VERSION=17c
endif
ifndef ANDROID_SDK_TOOLS_VERSION
    ANDROID_SDK_TOOLS_VERSION=4333796
endif
ifndef ANDROID_SDK_BUILD_TOOLS_VERSION
	ANDROID_SDK_BUILD_TOOLS_VERSION=28.0.2
endif
ifndef ANDROID_HOME
    ANDROID_HOME=$(HOME)/.android
endif
ifndef ANDROID_API_LEVEL
    ANDROID_API_LEVEL=27
endif

ANDROID_SDK_HOME=$(ANDROID_HOME)/android-sdk
ANDROID_SDK_TOOLS_ARCHIVE=sdk-tools-$(target_os)-$(ANDROID_SDK_TOOLS_VERSION).zip
ANDROID_SDK_TOOLS_DL_URL=https://dl.google.com/android/repository/$(ANDROID_SDK_TOOLS_ARCHIVE)

ANDROID_NDK_HOME=$(ANDROID_HOME)/android-ndk
ANDROID_NDK_FOLDER=$(ANDROID_HOME)/android-ndk-r$(ANDROID_NDK_VERSION)
ANDROID_NDK_ARCHIVE=android-ndk-r$(ANDROID_NDK_VERSION)-$(target_os)-x86_64.zip
ANDROID_NDK_DL_URL=https://dl.google.com/android/repository/$(ANDROID_NDK_ARCHIVE)

$(info Android SDK home is           : $(ANDROID_SDK_HOME))
$(info Android NDK home is           : $(ANDROID_NDK_HOME))
$(info Android SDK download url is   : $(ANDROID_SDK_TOOLS_DL_URL))
$(info Android NDK download url is   : $(ANDROID_NDK_DL_URL))
$(info Android API level is          : $(ANDROID_API_LEVEL))
$(info Android NDK version is        : $(ANDROID_NDK_VERSION))
$(info JAVA_HOME is                  : $(JAVA_HOME))

all: install_sdk install_ndk

install_sdk: download_android_sdk extract_android_sdk update_android_sdk

install_ndk: download_android_ndk extract_android_ndk

ensure_dir:
ifeq ($(target_os), darwin)
	mkdir -p $(1)
else
	mkdir --parents $(1)
endif

download_android_sdk:
	curl --location --progress-bar --continue-at - \
	$(ANDROID_SDK_TOOLS_DL_URL) --output $(ANDROID_SDK_TOOLS_ARCHIVE)

download_android_ndk:
	curl --location --progress-bar --continue-at - \
	$(ANDROID_NDK_DL_URL) --output $(ANDROID_NDK_ARCHIVE)

extract_android_sdk:
	$(call ensure_dir $(ANDROID_SDK_HOME))
	unzip -q $(ANDROID_SDK_TOOLS_ARCHIVE) -d $(ANDROID_SDK_HOME)

extract_android_ndk:
	$(call ensure_dir $(ANDROID_NDK_FOLDER))
	unzip -q $(ANDROID_NDK_ARCHIVE) -d $(ANDROID_HOME) \
	&& ln -sfn $(ANDROID_NDK_FOLDER) $(ANDROID_NDK_HOME)

# updates Android SDK, install Android API, Build Tools and accept licenses
update_android_sdk:
	touch $(ANDROID_HOME)/repositories.cfg
	yes | $(ANDROID_SDK_HOME)/tools/bin/sdkmanager --licenses > /dev/null
	$(ANDROID_SDK_HOME)/tools/bin/sdkmanager "build-tools;$(ANDROID_SDK_BUILD_TOOLS_VERSION)" > /dev/null
	$(ANDROID_SDK_HOME)/tools/bin/sdkmanager "platforms;android-$(ANDROID_API_LEVEL)" > /dev/null
	# Set avdmanager permissions (executable)
	chmod +x $(ANDROID_SDK_HOME)/tools/bin/avdmanager
