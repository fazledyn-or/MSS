# -*- coding: utf-8 -*-
"""

    tests._test_msui.test_kmloverlay_dockwidget
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    This module provides pytest functions to tests msui.kmloverlay_dockwidget

    This file is part of MSS.

    :copyright: Copyright 2017 Joern Ungermann
    :copyright: Copyright 2017-2023 by the MSS team, see AUTHORS.
    :license: APACHE-2.0, see LICENSE for details.

    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.
"""

import os
import fs
import sys
import mock
from PyQt5 import QtWidgets, QtCore, QtTest, QtGui
from tests.constants import ROOT_DIR
import mslib.msui.kmloverlay_dockwidget as kd

sample_path = os.path.join(os.path.dirname(__file__), "..", "data")
save_kml = os.path.join(ROOT_DIR, "merged_file123.kml")


# ToDo refactoring, extract helper methods into functions
# ToDo review needed helper functions
class Test_KmlOverlayDockWidget(object):

    def setup_method(self):
        self.application = QtWidgets.QApplication(sys.argv)
        self.view = mock.Mock()
        self.view.map = mock.Mock(side_effect=lambda x, y: (x, y))
        self.view.map.plot = mock.Mock(return_value=[mock.Mock()])
        self.view.map.gcpoints_path = mock.Mock(side_effect=lambda x, y: (x, y))

        self.window = kd.KMLOverlayControlWidget(view=self.view)
        self.window.show()
        QtWidgets.QApplication.processEvents()
        QtTest.QTest.qWaitForWindowExposed(self.window)
        # start load test
        self.window.select_all()
        self.window.remove_file()
        QtWidgets.QApplication.processEvents()

    def teardown_method(self):
        QtWidgets.QApplication.processEvents()
        self.application.quit()
        QtWidgets.QApplication.processEvents()
        self.window.close()
        if os.path.exists(save_kml):
            os.remove(save_kml)

    def count_patches(self):
        return sum([len(_x["patch"].patches) for _x in self.window.dict_files.values() if _x["patch"] is not None])

    def select_file(self, file):  # Utility function for single file
        path = fs.path.join(sample_path, file)
        filename = (path,)  # converted to tuple
        self.window.select_file(filename)
        self.window.load_file()
        QtWidgets.QApplication.processEvents()
        return path

    def select_files(self):  # Utility function for multiple files
        for sample in ["folder.kml", "line.kml", "color.kml", "style.kml", "features.kml"]:
            path = fs.path.join(sample_path, sample)
            filename = (path,)  # converted to tuple
            self.window.select_file(filename)
            QtWidgets.QApplication.processEvents()

    @mock.patch("mslib.msui.kmloverlay_dockwidget.get_open_filenames",
                return_value=[fs.path.join(sample_path, "line.kml")])
    def test_get_file(self, mockopen):  # Tests opening of QFileDialog
        QtTest.QTest.mouseClick(self.window.btSelectFile, QtCore.Qt.LeftButton)
        QtWidgets.QApplication.processEvents()
        assert mockopen.call_count == 1

    @mock.patch("PyQt5.QtWidgets.QMessageBox")
    def test_select_file(self, mockbox):
        """
        Test All geometries and styles are being parsed without crashing
        """
        index = 0
        assert self.window.listWidget.count() == 0
        for sample in ["folder.kml", "line.kml", "color.kml", "style.kml"]:
            path = self.select_file(sample)
            QtTest.QTest.qWait(250)
            assert self.window.listWidget.item(index).checkState() == QtCore.Qt.Checked
            index = index + 1
        assert self.window.directory_location == path
        assert mockbox.critical.call_count == 0
        assert self.window.listWidget.count() == index
        assert len(self.window.dict_files) == index
        assert self.count_patches() == 9
        self.window.select_all()
        self.window.remove_file()

    @mock.patch("PyQt5.QtWidgets.QMessageBox")
    def test_select_file_error(self, mockbox):
        """
        Test that program mitigates loading a non-existing file
        """
        # load a non existing path
        self.window.select_all()
        self.window.remove_file()
        path = fs.path.join(sample_path, "satellite_predictor.txt")
        filename = (path,)  # converted to tuple
        self.window.select_file(filename)
        self.window.load_file()
        QtWidgets.QApplication.processEvents()
        assert mockbox.critical.call_count == 1
        self.window.listWidget.clear()
        self.window.dict_files = {}

    def test_remove_file(self):
        """
        Test removing all files except one
        """
        self.select_files()
        QtWidgets.QApplication.processEvents()
        self.window.listWidget.item(0).setCheckState(QtCore.Qt.Unchecked)
        QtTest.QTest.mouseClick(self.window.pushButton_remove, QtCore.Qt.LeftButton)
        assert self.window.listWidget.count() == 1
        assert len(self.window.dict_files) == 1
        self.window.select_all()
        self.window.remove_file()

    def test_remove_all_files(self):
        """
        Test removing all files
        """
        self.select_files()
        QtWidgets.QApplication.processEvents()
        assert self.window.listWidget.count() == 5
        QtTest.QTest.mouseClick(self.window.pushButton_remove, QtCore.Qt.LeftButton)
        QtWidgets.QApplication.processEvents()
        assert self.window.listWidget.count() == 0  # No items in list
        assert self.window.dict_files == {}  # Dictionary should be empty
        assert self.count_patches() == 0

    @mock.patch("PyQt5.QtWidgets.QMessageBox")
    @mock.patch("mslib.msui.kmloverlay_dockwidget.get_save_filename", return_value=save_kml)
    def test_merge_file(self, mocksave, mockbox):
        """
        Test merging files into a single file without crashing
        """
        self.select_files()
        QtWidgets.QApplication.processEvents()
        QtTest.QTest.mouseClick(self.window.pushButton_merge, QtCore.Qt.LeftButton)
        QtWidgets.QApplication.processEvents()
        assert mocksave.call_count == 1
        assert os.path.exists(save_kml)

    @mock.patch("PyQt5.QtWidgets.QColorDialog.getColor", return_value=QtGui.QColor())
    def test_customize_kml(self, mock_colour_button):
        """
        Test the pushbutton for color and double spin box for linewidth and checking specific
        file gets desired linewidth and colour
        """
        path = self.select_file("line.kml")  # selects file and returns path
        assert self.window.listWidget.count() == 1
        item = self.window.listWidget.item(0)
        rect = self.window.listWidget.visualItemRect(item)
        # in testing, need to add mouseclick and click the listWidget item
        QtTest.QTest.mouseClick(self.window.listWidget.viewport(),
                                QtCore.Qt.LeftButton,
                                pos=rect.center())
        QtWidgets.QApplication.processEvents()

        # Clicking on Push Button Colour
        QtTest.QTest.mouseClick(self.window.pushButton_color, QtCore.Qt.LeftButton)
        QtWidgets.QApplication.processEvents()
        assert mock_colour_button.call_count == 1

        # Testing the Double Spin Box for linewidth
        self.window.dsbx_linewidth.setValue(3)
        assert self.window.dsbx_linewidth.value() == 3

        # Testing the dictionary of files for color and linewidth
        assert self.window.dict_files[path]["color"] == (0, 0, 0, 1)
        assert self.window.dict_files[path]["linewidth"] == 3

        self.window.remove_file()
        assert self.window.listWidget.count() == 0

    def test_check_uncheck(self):
        """
        Tests 'Displays plot on map when file is checked' and vice versa
        """
        self.select_file("line.kml")
        assert self.window.listWidget.item(0).checkState() == QtCore.Qt.Checked
        assert len([_x for _x in self.window.dict_files.values() if _x["patch"] is not None]) == 1
        self.window.listWidget.item(0).setCheckState(QtCore.Qt.Unchecked)
        assert self.window.listWidget.item(0).checkState() == QtCore.Qt.Unchecked
        assert len([_x for _x in self.window.dict_files.values() if _x["patch"] is not None]) == 0
        self.window.select_all()
        self.window.remove_file()

    # Matplotlib Plots Testing
    def test_kml_patches(self):
        """
        Tests the type of patches plotted by each Test Sample File
        """
        self.select_file("line.kml")
        assert self.count_patches() == 1  # 1 LineString Geometry Patch
        self.window.remove_file()

        self.select_file("folder.kml")
        assert self.count_patches() == 3  # 1 Point, 1 Polygon, 1 Text Patch
        self.window.remove_file()

        self.select_file("color.kml")
        assert self.count_patches() == 1  # 1 Polygon Patch
        self.window.remove_file()

        self.select_file("style.kml")
        assert self.count_patches() == 4  # 1 Point, 1 Text, 1 Polygon, 1 LineString Patch
        self.window.remove_file()

        self.select_file("features.kml")
        assert self.count_patches() == 17  # 3 Points, 11 LineStrings, 3 Polygons Patch
        self.window.remove_file()

        self.select_file("polygon_inner.kml")
        assert self.count_patches() == 5  # 5 Polygons Patch
        self.window.remove_file()

        self.select_file("Multilinestrings.kml")
        assert self.count_patches() == 10  # 10 LineStrings Patch
        self.window.remove_file()

        self.select_file("geometry_collection.kml")
        assert self.count_patches() == 3  # 1 Point, 1 Text, 1 Polygon Patch
        self.window.remove_file()

    # this fails with dependencies given by python 3.10 and MSS before 7.0.1
    # because we have not verified to pass always int to QtGui.QColor
    def test_show_color_icon(self):
        filename = self.select_file("fir.kml")  # selects file and returns path
        assert filename.endswith('kml')
        clr = [0.6666666, 0.6666666, 0.6666666]
        assert self.window.show_color_icon(filename, clr) is not None
