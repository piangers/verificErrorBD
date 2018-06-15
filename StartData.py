# -*- coding: utf-8 -*-

from qgis.core import QGis, QgsFeatureRequest, QgsVectorLayer, QgsVectorLayer, QgsMapLayerRegistry, QgsFeature, QgsField, QgsGeometry, QGis
from PyQt4.QtGui import QIcon, QAction
from PyQt4.QtCore import QObject, SIGNAL, QVariant
from PyQt4.QtSql import QSqlDatabase, QSqlQuery
import resources_rc  
from qgis.gui import QgsMessageBar

class StartData:

    def __init__(self, iface):
        #
        self.iface = iface

        self.tableSchema = 'edgv'
        self.geometryColumn = 'geom'
        self.keyColumn = 'id'

    def initGui(self):
         
        # cria uma ação que iniciará a configuração do plugin 
        pai = self.iface.mainWindow()
        icon_path = ':/plugins/StartData/icon.png'
        self.action = QAction (QIcon (icon_path),u"Acessa banco de dados para revisão", pai)
        self.action.setObjectName ("Stard database")
        self.action.setStatusTip(None)
        self.action.setWhatsThis(None)
        self.action.triggered.connect(self.run)
        # Adicionar o botão icone
        self.iface.addToolBarIcon (self.action) 

    def unload(self):
        # remove o item de ícone do QGIS GUI.
        self.iface.removeToolBarIcon (self.action)
        
        
    def run(self):
        connection = QSqlDatabase.addDatabase('QPSQL')
        connection.setHostName('10.25.163.12')
        connection.setPort(5432)
        connection.setUserName('fme')
        connection.setPassword('tassofragoso')
        connection.setDatabaseName('rs_rf1')
        if not connection.isOpen():
            if not connection.open():
                print 'Error connecting to database!'
                return
            else:
                print 'Connection succeeded!'

        
        layer = self.iface.activeLayer()
        layerCrs = layer.crs().authid()

        flagsLayerName = layer.name() + "_flags"
        flagsLayerExists = False

        for l in QgsMapLayerRegistry.instance().mapLayers().values():
            if l.name() == flagsLayerName:
                self.flagsLayer = l
                self.flagsLayerProvider = l.dataProvider()
                flagsLayerExists = True
                break

        if flagsLayerExists == False:
            tempString = "Point?crs="
            tempString += str(layerCrs)

            self.flagsLayer = QgsVectorLayer(tempString, flagsLayerName, "memory")
            self.flagsLayerProvider = self.flagsLayer.dataProvider()
            self.flagsLayerProvider.addAttributes([QgsField("id", QVariant.Int), QgsField("motivo", QVariant.String)])
            self.flagsLayer.updateFields()


        self.flagsLayer.startEditing()
        ids = [feat.id() for feat in self.flagsLayer.getFeatures()]
        self.flagsLayer.deleteFeatures(ids)
        self.flagsLayer.commitChanges()
        
        lista_fid = "("
        
        for f in layer.getFeatures():
            lista_fid += str(f.id())
            lista_fid += ", "
        
        lista_fid = lista_fid[:len(lista_fid)-2]
        lista_fid += ")"

        source = layer.source().split(" ")
        self.tableName = ""
        layerExistsInDB = False
        for i in source:
            if "table=" in i or "layername=" in i:
                self.tableName = source[source.index(i)].split(".")[1]
                self.tableName = self.tableName.replace('"', '')
                layerExistsInDB = True
                break

        if layerExistsInDB == False:
            self.iface.messageBar().pushMessage("Erro", \
                                            u"provedor da camada corrente não é em banco de dados!", \
                                            level=QgsMessageBar.CRITICAL, \
                                            duration=10)
            return

        query_string  = '''select distinct (reason(ST_IsValidDetail(f."{2}",0))) AS motivo, '''
        query_string += '''ST_AsText(ST_Multi(ST_SetSrid(location(ST_IsValidDetail(f."{2}",0)), ST_Srid(f.{2})))) as local from '''
        query_string += '''(select "{3}", "{2}" from only "{0}"."{1}"  where ST_IsValid("{2}") = 'f' and {3} in {4}) as f''' # Aqui o where deve passar os ids passados da tabela 
        query_string  = query_string.format(self.tableSchema, self.tableName, self.geometryColumn, self.keyColumn, lista_fid)
        
        query = QSqlQuery(query_string)
        
        self.flagsLayer.startEditing()
        flagCount = 0

        while query.next():
            motivo = query.value(0).toString()
            local = query.value(1).toString()
            flagId = flagCount

            flagFeat = QgsFeature()
            flagGeom = QgsGeometry.fromWkt(local)
            flagFeat.setGeometry(flagGeom)
            flagFeat.setAttribute("id", flagId)
            flagFeat.setAttribute("motivo", motivo)

            self.flagsLayerProvider.addFeature(flagFeat)

            flagCount += 1

            # SE FOR PARA PREENCHER TABELA NO BANCO, ESTE CÓDIGO VOLTA!!
                # O QUE A QUERY RESPONDE:
                # # - O id DA FEIÇÃO
                # # - O motivo DE SER INVÁLIDA
                # # - A geometria DO LOCAL ONDE HOUVE FLAG

            # schema_flags = 'edgv'
            # tabela_flags = 'aux_valida_p'
            # # QGIS DEVE PASSAR OS VALORES
        
            # insert_string = '''insert into {0}.{1} (observacao, geom) VALUES ('{2}', '{3}')'''.format(schema_flags, tabela_flags, motivo, local)
              
            # insert_query = QSqlQuery()
            # insert_query.prepare(insert_string)
            # insert_query.exec_()


        QgsMapLayerRegistry.instance().addMapLayer(self.flagsLayer)

        self.iface.messageBar().pushMessage("Aviso", \
                                            "foram geradas " + str(flagCount) + " flags para a camada \"" + layer.name() + "\" !", \
                                            level=QgsMessageBar.INFO, \
                                            duration=10)

        print 'Foram geradas ' + str(flagCount) + ' flags!'


        print query.lastError().text()