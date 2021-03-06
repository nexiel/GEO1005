# -*- coding: utf-8 -*-
"""
/***************************************************************************
 criminal_counterDockWidget
                                 A QGIS plugin
 This plugin helps the policeman on duty to catch criminals
                             -------------------
        begin                : 2018-01-07
        git sha              : $Format:%H$
        copyright            : (C) 2018 by group6
        email                : ^dushenglan940128@163.com
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""

import os
import random

from PyQt4.QtGui import *
from qgis.core import *
from qgis.utils import iface
from PyQt4 import QtGui, uic
from PyQt4.QtCore import pyqtSignal, QVariant
from qgis.networkanalysis import *
from time import gmtime, strftime
from qgis.gui import *
import processing
import resources
from . import utility_functions as uf

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'criminal_counter_dockwidget_base.ui'))


class criminal_counterDockWidget(QtGui.QDockWidget, FORM_CLASS):

    closingPlugin = pyqtSignal()

    def __init__(self, parent=None):
        """Constructor."""
        super(criminal_counterDockWidget, self).__init__(parent)
        # Set up the user interface from Designer.
        # After setupUI you can access any designer object by doing
        # self.<objectname>, and you can use autoconnect slots - see
        # http://qt-project.org/doc/qt-4.8/designer-using-a-ui-file.html
        # #widgets-and-dialogs-with-auto-connect
        self.setupUi(self)

        # define globals
        self.iface = iface
        self.canvas = self.iface.mapCanvas()

        self.plugin_dir = os.path.dirname(__file__)

        self.iface.addProject(unicode(self.plugin_dir+"/data/criminal_data.qgs"))

        # tab case input
        self.tab_Main.setCurrentIndex(0)
        self.comboBox_Rank.activated.connect(self.setCasebyRank)
        self.comboBox_Time.activated.connect(self.setCasebyTime)
        self.Button_SelectCase.clicked.connect(self.selectCase)
        self.selectPoint = QgsMapToolEmitPoint(self.canvas)
        self.selectPoint.canvasClicked.connect(self.getCase)

        self.button_run.clicked.connect(self.runcase)
        self.button_cancel.clicked.connect(self.cancel)
        self.caseID = -1
        
        # tab analysis
        self.counter=0
        self.graph = QgsGraph()
        self.tied_points = []
        self.policelist = []
        self.button_add.clicked.connect(self.addnode)
        self.button_subtract.clicked.connect(self.removeNodefromTable)
        self.button_calculate.clicked.connect(self.calculation)
        self.button_undo.clicked.connect(self.deleteRoutes)

        self.emitPoint = QgsMapToolEmitPoint(self.canvas)
        self.emitPoint.canvasClicked.connect(self.getPoint)
        self.button_StartCounter.clicked.connect(self.reportMessage)
        self.button_ClearCase.clicked.connect(self.clearReport)
        
        # tab report
        self.button_save.clicked.connect(self.saveReport)
        self.button_save_2.clicked.connect(self.saveMap)
        self.button_clear.clicked.connect(self.clearReport)

        # add button icons
        self.label.setPixmap(QtGui.QPixmap(':Logo_Criminal_Counter.png'))
        
        # initialisation
        self.loadLayers()
        self.deleteRoutes()

    def closeEvent(self, event):
        self.closingPlugin.emit()
        event.accept()

###
#Incidents input
###
    def loadLayers(self):
        # load incidents layer and initialize two combobox
        self.comboBox_Rank.clear()
        self.comboBox_Time.clear()
        incident_layernm = "Incidents"
        incident_layer = uf.getLegendLayerByName(self.iface, incident_layernm)
        self.setOriginalCombox(incident_layer)
        self.canvas.zoomScale(20000.0)
        self.tab_Analysis_2.setDisabled(True)
        self.tab_Reporting_2.setDisabled(True)


    def setOriginalCombox(self, layer):
        # initialize comboboxes based on order of rank or time
        rank_fieldnm = "Urgency_R"
        time_fieldnm = "Time"
        if uf.fieldExists(layer, rank_fieldnm) and uf.fieldExists(layer, time_fieldnm):
            sorted_rank = self.orderbyAttribute(layer, rank_fieldnm)
            sorted_time = self.orderbyAttribute(layer, time_fieldnm)
            self.comboBox_Rank.addItems(sorted_rank)
            self.comboBox_Time.addItems(sorted_time)
        else:
            return

    def orderbyAttribute(self, layer, attributenm):
        # order the incidents according to one attribute
        # return the sorted list of case info
        attribute, ids = uf.getFieldValues(layer, attributenm)
        tp_sorted = sorted(zip(attribute,ids), reverse = True)
        lst_sorted_id = []
        for item in tp_sorted:
            lst_sorted_id.append(item[1])
        incidents_info = []
        for ids in lst_sorted_id:
            for feat in layer.getFeatures():
                if ids == feat.id():
                    incidents_info.append(feat.attributes()[6])
        return incidents_info

    def setCasebyRank(self):
        # select the incident in rank combobox
        case_no = self.comboBox_Rank.currentText()
        self.writeCaseList(case_no)

    def setCasebyTime(self):
        # select the incident in time combobox
        case_no = self.comboBox_Time.currentText()
        self.writeCaseList(case_no)

    def writeCaseList(self, caseno):
        # write the case information in the list according to the case number
        layer = uf.getLegendLayerByName(self.iface,"Incidents")
        self.list_case.clear()
        layer.setSelectedFeatures([])
        self.caseID = caseno
        case_info = []
        for feat in layer.getFeatures():
            att = feat.attributes()[6]
            if att == caseno:
                case_info.append("case number: " + feat.attributes()[6])
                case_info.append("rank: " + str(feat.attributes()[0]))
                case_info.append("criminal id: " + str(feat.attributes()[1]))
                case_info.append("criminal information: " + feat.attributes()[2])
                case_info.append("case information: " + feat.attributes()[3])
                case_info.append("case name: " + feat.attributes()[4])
                case_info.append("time: " + feat.attributes()[5])

                self.list_case.addItems(case_info)
                layer.setSelectedFeatures([feat.id()])
                break

    def selectCase(self):
        self.userTool = self.canvas.mapTool()
        self.canvas.setMapTool(self.selectPoint)

    def getCase(self, point, mouseButton):
        self.canvas.unsetMapTool(self.selectPoint)
        self.canvas.setMapTool(self.userTool)
        if point:
            width = self.iface.mapCanvas().mapUnitsPerPixel() * 50
            rect = QgsRectangle(point.x() - width,
                                point.y() - width,
                                point.x() + width,
                                point.y() + width)
            layer = uf.getLegendLayerByName(self.iface, "Incidents")
            rect = self.iface.mapCanvas().mapRenderer().mapToLayerCoordinates(layer, rect)
            for feat in layer.getFeatures():
                xy = feat.geometry().asPoint()
                # self.list_case.addItems([str(point.x() - width)])
                # self.list_case.addItems([str(xy[0]),str(xy[1])])
                pt = QgsPoint(xy[0], xy[1])
                if rect.contains(pt):
                    layer.setSelectedFeatures([feat.id()])
                    self.writeCaseList(feat.attributes()[6])
                    self.canvas.unsetMapTool(self.userTool)

                    break

    def runcase(self):
        # put the focus on the selected incident and jump to analysis part
        if self.caseID == -1:
            QMessageBox.information(None, "Warning:", "Please select a case you want to handle!")
            return
        self.tab_Analysis_2.setDisabled(False)
        self.tab_Case.setDisabled(True)
        self.tab_Main.setCurrentIndex(1)
        layer = uf.getLegendLayerByName(self.iface, "Incidents")
        self.canvas.zoomToSelected(layer)
        self.canvas.zoomScale(5000.0)
        self.canvas.refresh()

    def cancel(self):
        # clear selection of incidents
        layer = uf.getLegendLayerByName(self.iface, "Incidents")
        layer.setSelectedFeatures([])
        #self.loadLayers()
        self.list_case.clear()
        self.caseID = -1
        self.canvas.zoomScale(20000.0)

###
# Node Input
###

    def addnode(self):
        # remember currently selected tool
        nodes = uf.getLegendLayerByName(self.iface, "Nodes")
        nodes.startEditing()
        self.userTool = self.canvas.mapTool()
        # activate coordinate capture tool
        self.canvas.setMapTool(self.emitPoint)

    def getPoint(self, mapPoint, mouseButton):
        # change tool so you don't get more than one POI
        self.canvas.unsetMapTool(self.emitPoint)
        self.canvas.setMapTool(self.userTool)
        if mapPoint:
            # here do something with the point
            nodes = uf.getLegendLayerByName(self.iface, "Nodes")
            pr=nodes.dataProvider()
            fet=QgsFeature()
            fet.setGeometry(QgsGeometry.fromPoint(mapPoint))
            pr.addFeatures([fet])
            nodes.commitChanges()
            self.refreshCanvas(nodes)
            self.updateNodeTable(nodes)

    def updateNodeTable(self, layer):
        # update the node table and visualize the node in the table
        self.table_Node.clear()
        lst_nodeID = []
        for feature in layer.getFeatures():
            lst_nodeID.append(feature.id()+1)
        self.table_Node.setColumnCount(1)
        self.table_Node.setHorizontalHeaderLabels(["Blockade No"])
        self.table_Node.setRowCount(len(lst_nodeID))
        for i, item in enumerate(lst_nodeID):
            self.table_Node.setItem(i, 0, QtGui.QTableWidgetItem(str(item)))
        self.table_Node.resizeRowsToContents()

    def removeNodefromTable(self):
        # remove selected node from the table
        nodes = uf.getLegendLayerByName(self.iface, "Nodes")
        items = self.table_Node.selectedItems()
        if items:
            for item in items:
                nodeID = int(item.text())-1
                nodes.startEditing()
                nodes.deleteFeature(nodeID)
            nodes.commitChanges()
            self.updateNodeTable(nodes)
            self.refreshCanvas(nodes)
        else:
            QMessageBox.information(None, "Warning:", "Please select the blockades you want to remove in the table!")
            return

###
# Route Creation
###
    def buildNetwork(self, nodePoint, policePoint):
        self.network_layer = uf.getLegendLayerByName(self.iface, "Roads_rotterdamcut")
        if self.network_layer:
            # get the points to be used as origin and destination
            # in this case gets the centroid of the selected features
            selected_sources=self.network_layer.selectedFeatures()
            source_points = [nodePoint]+[policePoint]
            # build the graph including these points
            if len(source_points) > 1:
                self.graph, self.tied_points = uf.makeUndirectedGraph(self.network_layer, source_points)
                # the tied points are the new source_points on the graph
        return

    def calculation(self):
        # calculate the nearest policeman and shortest path for each node selected by the user
        nodes_layer = uf.getLegendLayerByName(self.iface, "Nodes")
        nodes = nodes_layer.getFeatures()
        routes_layer = uf.getLegendLayerByName(self.iface, "Routes")



        if self.table_Node.rowCount() == 0:
            QMessageBox.information(None, "Warning:", "Please create the blockades first!")
            return

        if self.counter==1:
            QMessageBox.information(None, "Warning:", "Routes have already been created!")
            return
        
        self.table_PoliceJob.clear()
        self.table_PoliceJob.setColumnCount(2)
        self.table_PoliceJob.setHorizontalHeaderLabels(["Policeman", "will go to the node"])

        for node in nodes:
            policeman = self.getNearestPoliceman(node)
            self.getShortestPath(node, policeman)
            self.writeJobTable(node, policeman)
        self.refreshCanvas(routes_layer)
        self.counter=1

    def getNearestPoliceman(self, point):
        # find a nearest policeman for a given point(node)
        policeman_layer = uf.getLegendLayerByName(self.iface, "Policemen")
        if policeman_layer:
            provider = policeman_layer.dataProvider()
            police_index = QgsSpatialIndex()
            feature = QgsFeature()
            fit = provider.getFeatures()
            while fit.nextFeature(feature):
                if feature.attributes()[2] == "Yes":
                    if not feature.attributes()[4] == 0:
                        police_index.insertFeature(feature)
            xy_node = point.geometry().asPoint()
            pt_node = QgsPoint(xy_node[0], xy_node[1])
            nearest_policeID = police_index.nearestNeighbor(pt_node, 1)[0]
            nearest_police = QgsFeature()
            for feat in policeman_layer.getFeatures():
                if feat.id() == nearest_policeID:
                    nearest_police = feat
                    policeman_layer.startEditing()
                    feat['Available2'] = 0
                    policeman_layer.updateFeature(feat)
                    policeman_layer.commitChanges()
                    break

            return nearest_police

    def getShortestPath(self, node, police):
        # obtain the shortest path between a given node and a given policeman
        roads = uf.getLegendLayerByName(self.iface, "Roads_rotterdamcut")
        provider = roads.dataProvider()
        spIndex = QgsSpatialIndex()  # create spatial index object
        feat = QgsFeature()
        fit = provider.getFeatures()  # gets all features in layer
        # insert features to index
        while fit.nextFeature(feat):
            spIndex.insertFeature(feat)

        xy_node = node.geometry().asPoint()
        pt_node = QgsPoint(xy_node[0], xy_node[1])
        xy_police = police.geometry().asPoint()
        pt_police = QgsPoint(xy_police[0], xy_police[1])

        self.buildNetwork(pt_node, pt_police)

        options = len(self.tied_points)
        if options > 1:
            # origin and destination are given as an index in the tied_points list
            origin = 0
            destination = random.randint(1, options - 1)
            # calculate the shortest path for the given origin and destination
            path = uf.calculateRouteDijkstra(self.graph, self.tied_points, origin, destination)
            # store the route results in temporary layer called "Routes"
            routes_layer = uf.getLegendLayerByName(self.iface, "Routes")
            # create one if it doesn't exist
            if not routes_layer:
                attribs = ['id']
                types = [QtCore.QVariant.String]
                routes_layer = uf.createTempLayer('Routes', 'LINESTRING', self.network_layer.crs().postgisSrid(),
                                                  attribs, types)
                # change layer styles
                symbols = routes_layer.rendererV2().symbols()
                symbol = symbols[0]
                symbol.setColor(QColor("brown"))
                symbol.setWidth(1.5)
                uf.loadTempLayer(routes_layer)
                routes_layer.setLayerName('Routes')
            prov = routes_layer.dataProvider()
            fet = QgsFeature()
            fet.setGeometry(QgsGeometry.fromPolyline(path))
            prov.addFeatures([fet])
            #uf.insertTempFeatures(routes_layer, [path], [['testing', 100.00]])
        roads.removeSelection()


    def writeJobTable(self, point, policeman):
        # write the assignment of policeman to the list
        job_info = []
        job_info.append("policeman " + policeman.attributes()[1] + " will go to the node " + str(point.id()))
        self.policelist.append(policeman.attributes()[1])
        currentRow = self.table_PoliceJob.rowCount()
        self.table_PoliceJob.insertRow(currentRow)
        self.table_PoliceJob.setItem(currentRow,0,QtGui.QTableWidgetItem(policeman.attributes()[1]))
        self.table_PoliceJob.setItem(currentRow,1,QtGui.QTableWidgetItem(str(point.id()+1)))
        self.table_PoliceJob.horizontalHeader().setResizeMode(0, QtGui.QHeaderView.ResizeToContents)
        self.table_PoliceJob.horizontalHeader().setResizeMode(1, QtGui.QHeaderView.Stretch)
        self.table_PoliceJob.resizeRowsToContents()


    def deleteRoutes(self):
        routes_layer = uf.getLegendLayerByName(self.iface, "Routes")
        nodes = uf.getLegendLayerByName(self.iface, "Nodes")
        policeman_layer = uf.getLegendLayerByName(self.iface, "Policemen")
        with edit(routes_layer):
            listOfIds = [feat.id() for feat in routes_layer.getFeatures()]
            routes_layer.deleteFeatures(listOfIds)
        with edit(nodes):
            listOfIds = [feat.id() for feat in nodes.getFeatures()]
            nodes.deleteFeatures(listOfIds)
        with edit(policeman_layer):
            for feature in policeman_layer.getFeatures():
                if feature.attributes()[4] == 0:
                    policeman_layer.startEditing()
                    feature['Available2'] = 1
                    policeman_layer.updateFeature(feature)
                    #policeman_layer.commitChanges()

        self.table_Node.clear()
        self.table_Node.setRowCount(0)
        self.table_PoliceJob.clear()
        self.table_PoliceJob.setRowCount(0)
        self.table_PoliceJob.setColumnCount(2)
        self.table_PoliceJob.setHorizontalHeaderLabels(["Policeman","will go to the node"])
        self.canvas.refresh()
        self.policelist = []
        self.counter=0

###
# Report output
###

    def reportMessage(self):
        # send a message to the user that order has been sent
        if self.caseID == -1 or self.policelist == []:
            QMessageBox.information(None, "Warning:", "Please create routes first!")
            return
        QMessageBox.information(None, "Message:", "Your command has been sent successfully!")
        self.tab_Main.setCurrentIndex(2)
        self.tab_Reporting_2.setDisabled(False)
        self.tab_Analysis_2.setDisabled(True)
        self.writeReportList()

    def writeReportList(self):
        # write the criminal counter log info to the report list
        counter_info = []
        str_time = strftime("%Y-%m-%d %H:%M:%S", gmtime())
        counter_info.append("on " + str_time + " (gmt)")
        counter_info.append("the case no: " + str(self.caseID) + " was handled")
        counter_info.append("following policemen executed this order:")
        for policename in self.policelist:
            counter_info.append(policename)
        self.list_summary.addItems(counter_info)

    def saveReport(self):
        path = QtGui.QFileDialog.getSaveFileName(self, 'Save File', '', 'TXT(*.txt)')
        if path:
            f_output = open(path, "w")
            for i in range(self.list_summary.count()):
                content = self.list_summary.item(i).text()
                f_output.write(content)
                f_output.write("\n")
            f_output.close()
            QMessageBox.information(None, "Message:", "Report has been saved successfully!")


    def saveMap(self):
        path = QtGui.QFileDialog.getSaveFileName(self, 'Save File', '', 'PNG(*.png)')
        if path != '':
            self.canvas.saveAsImage(path,None,"PNG")
            QMessageBox.information(None, "Message:", "Map has been saved successfully!")

    def clearReport(self):
        self.list_summary.clear()
        self.tab_Main.setCurrentIndex(0)
        self.deleteRoutes()
        layer = uf.getLegendLayerByName(self.iface, "Incidents")
        layer.setSelectedFeatures([])
        self.list_case.clear()
        self.loadLayers()
        self.tab_Case.setDisabled(False)
        self.tab_Reporting_2.setDisabled(True)
        self.caseID = -1
        self.canvas.zoomScale(20000.0)

    def refreshCanvas(self, layer):
        # refresh canvas after changes
        if self.canvas.isCachingEnabled():
            layer.setCacheImage(None)
        else:
            self.canvas.refresh()
