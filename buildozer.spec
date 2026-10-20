[app]
title = FileManager
package.name = filemanager
package.domain = org.test
source.dir = .
source.include_exts = py,png,jpg,kv,atlas
version = 0.1

android.permissions = READ_EXTERNAL_STORAGE, WRITE_EXTERNAL_STORAGE, INTERNET, QUERY_ALL_PACKAGES

android.add_manifest_placeholders = android:requestLegacyExternalStorage="true"

requirements = python3,kivy,pyjnius,android
