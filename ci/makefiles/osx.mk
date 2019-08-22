
ifndef ANDROID_HOME
    ANDROID_HOME=$(HOME)/.android
endif

all: update_brew install_java upgrade_cython install_android_ndk_sdk install_p4a


update_brew:
	# update brew (will install python3)
	python --version
	brew update
	python3 --version

install_java:
	brew tap adoptopenjdk/openjdk
	brew cask install adoptopenjdk8
	/usr/libexec/java_home -V

upgrade_cython:
	pip3 install --upgrade Cython==0.28.6

install_android_ndk_sdk:
	mkdir -p $(ANDROID_HOME)
	make -f ci/makefiles/android.mk target_os=darwin JAVA_HOME=`/usr/libexec/java_home -v 1.8`

install_p4a:
	pip3 install -e .
