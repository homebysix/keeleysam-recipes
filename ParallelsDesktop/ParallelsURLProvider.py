#!/usr/bin/env python
#
# ParallelsURLProvider, version 2013.08.08
# Copyright 2013 Samuel Keeley, derived from BarebonesURLProvider by Timothy Sutton
# Thanks to Michael Lynn for help with xml.dom.minidom
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import

import xml.dom.minidom

from autopkglib import Processor, ProcessorError, URLGetter

__all__ = ["ParallelsURLProvider"]


class ParallelsURLProvider(URLGetter):
    description = "Provides a version, description, and DMG download for the Parallels product given."
    input_variables = {
        "product_name": {
            "required": True,
            "description": "Product to fetch URL for. For example: ParallelsDesktop15.",
        },
    }
    output_variables = {
        "version": {
            "description": "Version of the product.",
        },
        "url": {
            "description": "Download URL.",
        },
        "description": {
            "description": "Update description."
        }
    }
    __doc__ = description


    def generate_update_feed(self, product_name):
        '''Given a product name, generate the URL for the appropriate update XML feed.'''

        # Determine and validate major version
        try:
            maj_vers = int(product_name.replace('ParallelsDesktop', ''))
        except (ValueError, TypeError):
            raise ProcessorError('Invalid product name: %s' % product_name)
        if not maj_vers:
            raise ProcessorError('Invalid product name: %s' % product_name)

        # Generate XML feed URL
        url_template = "http://update.parallels.com/desktop/v%s/parallels/parallels_updates.xml"
        if maj_vers < 4:
            raise ProcessorError('Parallels versions less than 4 are not supported.')
        if maj_vers < 7:
            update_feed = url_template % (str(maj_vers) + '/en_us')
        else:
            update_feed = url_template % str(maj_vers)

        # Validate URL
        curl_cmd = self.prepare_curl_cmd()
        curl_cmd.extend(["--head", update_feed])
        output = self.download_with_curl(curl_cmd)
        if "200 OK" not in output:
            raise ProcessorError('Unable to download update feed for %s' % product_name)

        return update_feed


    def main(self):
        '''Main process.'''

        # Determine update feed based on provided product name
        prod = self.env.get("product_name")
        update_feed = self.generate_update_feed(prod)

        # Download and parse update feed
        manifest_str = self.download(update_feed)
        the_xml = xml.dom.minidom.parseString(manifest_str)
        products = the_xml.getElementsByTagName('Product')

        # Iterate through listed products and find 'Parallels Desktop'
        parallels = None
        for a_product in products:
            if a_product.getElementsByTagName(
                    'ProductName')[0].firstChild.nodeValue == u'Parallels Desktop':
                parallels = a_product
                v_major = parallels.getElementsByTagName(
                    'Major')[0].firstChild.nodeValue
                v_minor = parallels.getElementsByTagName(
                    'Minor')[0].firstChild.nodeValue
                v_sub_minor = parallels.getElementsByTagName(
                    'SubMinor')[0].firstChild.nodeValue
                v_sub_sub_minor = parallels.getElementsByTagName(
                    'SubSubMinor')[0].firstChild.nodeValue
                version = '.'.join(
                    [v_major, v_minor, v_sub_minor, v_sub_sub_minor])
                update = parallels.getElementsByTagName('Update')[0]
                try:
                    description = [x.firstChild.nodeValue for x in update.getElementsByTagName(
                        'UpdateDescription') if x.firstChild.nodeValue.startswith('en_US')][0]
                    description = '<html><body>%s</body></html>' % (
                        description.split('#', 1)[-1])
                except:
                    description = [x.firstChild.nodeValue for x in update.getElementsByTagName(
                        'UpdateDescription')][0]
                url = update.getElementsByTagName(
                    'FilePath')[0].firstChild.nodeValue

        self.env["version"] = version
        self.env["description"] = description
        self.env["url"] = url
        self.output("Found URL %s" % self.env["url"])

if __name__ == "__main__":
    processor = ParallelsURLProvider()
    processor.execute_shell()
