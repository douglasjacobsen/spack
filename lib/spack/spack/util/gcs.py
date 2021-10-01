# Copyright 2013-2021 Lawrence Livermore National Security, LLC and other
# Spack Project Developers. See the top-level COPYRIGHT file for details.
#
# SPDX-License-Identifier: (Apache-2.0 OR MIT)

"""
This file contains the definition of the GCS Blob storage Class used to
integrate GCS Blob storage with spack buildcache.
"""

import os
import sys

import llnl.util.tty as tty

def gcs_client():
    from google.cloud import storage
    import google.auth

    storage_credentials, storage_project = google.auth.default()
    storage_client = storage.Client(storage_project,
                                    storage_credentials)
    return storage_client

class GCSBucket:
    def __init__(self, url, client=None):
        self. url = url
        self.name = self.url.netloc
        tty.debug("bucket_name = {}".format(self.name))

        if not client:
            self.client = gcs_client()
        else:
            self.client = client

        self.bucket = None

    def exists(self):
        if not self.bucket:
            try:
                self.bucket = self.client.bucket(self.name)
            except Exception as ex:
                tty.error("{}, Failed check for bucket existence".format(ex))
                sys.exit(1)
        return (self.bucket is not None)

    def create(self):
        if not self.bucket:
            self.bucket = self.client.create_bucket(self.name)

    def get_blob(self, blob_path):
        if self.exists():
            return self.bucket.get_blob(blob_path)
        return None

    def blob(self, blob_path):
        if self.exists():
            return self.bucket.blob(blob_path)
        return None

    def get_all_blobs(self, relative=True):
        if self.exists():
            try:
                all_blobs = self.bucket.list_blobs()
                blob_list = []

                if not relative:
                    # If we do not want relative paths, just return the list
                    for blob in all_blobs:
                        blob_list.append(blob.name)
                else:
                    # To create relative paths, strip everything before 'build_cache'
                    for blob in all_blobs:
                        p = blob.name.split('/')
                        try:
                            build_cache_index = p.index('build_cache')
                            blob_list.append(os.path.join(*p[build_cache_index + 1:]))
                        except ValueError as ex:
                            blob_list.append(os.path.join(*p[:]))

                        tty.debug("Blob name = {}, converted blob name = {}".format(blob.name, blob_list[-1]))

                return blob_list
            except Exception as ex:
                tty.error("{}, Could not get a list of all GCS blobs.".format(ex))
                sys.exit(1)

    def destroy(self):
        try:
            bucket_blobs = self.get_all_blobs(relative=False)
            batch_size = 1000

            num_blobs = len(bucket_blobs)
            for i in range(0, num_blobs, batch_size):
                with self.client.batch():
                    for j in range(i, min(i+batch_size, num_blobs)):
                        blob = self.blob(bucket_blobs[j])
                        blob.delete()
        except Exception as ex:
            tty.error("{}, Could not delete a blob in bucket {}.".format(ex, self.name))
            sys.exit(1)

        try:
            self.bucket.delete()
        except Exception as ex:
            tty.error("{}, Could not destroy bucket {}.".format(ex, self.name))
            sys.exit(1)

class GCSBlob:
    def __init__(self, url, client=None):

        self.url = url
        if url.scheme != 'gs':
            raise ValueError('Can not create GCS blob connection with scheme: {SCHEME}'
                             .format(SCHEME=url.scheme))

        if not client:
            self.client = gcs_client()
        else:
            self.client = client

        self.bucket = GCSBucket(url)

        if self.url.path[0] == '/':
            self.blob_path = self.url.path[1:]
        else:
            self.blob_path = self.url.path

        tty.debug("blob_path = {}".format(self.blob_path))

        if not self.bucket.exists():
            tty.warn("The bucket {} does not exist, it will be created"
                     .format(self.bucket.name))
            self.bucket.create()

    def get(self):
        return self.bucket.get_blob(self.blob_path)

    def exists(self):
        try:
            blob = self.bucket.blob(self.blob_path)
            exists = blob.exists()
        except Exception:
            return False

        return exists

    def delete_blob(self):
        try:
            blob = self.bucket.blob(self.blob_path)
            blob.delete()
        except Exception as ex:
            tty.error("{}, Could not delete gcs blob {}".format(ex, self.blob_path))

    def upload_to_blob(self, local_file_path):
        try:
            blob = self.bucket.blob(self.blob_path.lstrip("/"))
            blob.upload_from_filename(local_file_path)
        except Exception as ex:
            tty.error("{}, Could not upload {} to gcs blob storage"
                      .format(ex, local_file_path))
            sys.exit(1)

    def get_blob_byte_stream(self):
        return self.bucket.get_blob(self.blob_path).open(mode='rb')

    def get_blob_headers(self):
        blob = self.bucket.get_blob(self.blob_path)

        headers = {}
        headers['Content-type'] = blob.content_type
        headers['Content-encoding'] = blob.content_encoding
        headers['Content-language'] = blob.content_language
        headers['MD5Hash'] = blob.md5_hash

        return headers

