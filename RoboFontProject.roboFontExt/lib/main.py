from AppKit import *

import os

import vanilla.dialogs as dialogs
import vanilla

from mojo.events import addObserver
from mojo.UI import OpenGlyphWindow, OpenSpaceCenter, CurrentSpaceCenterWindow, OutputWindow

from lib.scripting.scriptTools import ScriptRunner
from lib.scripting.codeEditor import CodeEditor
from lib.baseObjects import CallbackWrapper

from plistlib import readPlist, writePlist


def OpenRoboFontProject(path):
    root = os.path.dirname(path)
    project = readPlist(path)

    documentController = NSDocumentController.sharedDocumentController()
    delegate = NSApp().delegate()

    openFileNames = [window.representedFilename() for window in NSApp().windows()]

    for fileName, data in project["documents"].items():

        isUntitled = fileName == "untitled"

        if not isUntitled:
            if not os.path.exists(fileName):
                fileName = os.path.abspath(os.path.join(root, fileName))

            if not os.path.exists(fileName):
                continue

            if fileName in openFileNames:
                continue

        data.sort(key=lambda item: item.get("name") != "FontWindow")

        for windowData in data:
            name = windowData["windowName"]
            x, y, w, h = windowData["frame"]

            if isUntitled:
                if name == "FontWindow":
                    RFont()
                elif name == "ScriptingWindow":
                    delegate.scriptingWindow_(None)
                elif name == "FeatureWindow":
                    delegate.newFeature_(None)

            else:
                url = NSURL.fileURLWithPath_(fileName)
                doc, error = documentController.openDocumentWithContentsOfURL_display_error_(url, True, None)
                if error:
                    delegate.application_openFile_(NSApp(), fileName)

            window = NSApp().mainWindow()

            vanillaWrapper = None
            if hasattr(window.delegate(), "vanillaWrapper"):
                vanillaWrapper = window.delegate().vanillaWrapper()

            if vanillaWrapper:
                font = CurrentFont()
                if name == "GlyphWindow":
                    window = OpenGlyphWindow(font[windowData["glyphName"]], newWindow=True)
                    window.w.getNSWindow().setFrame_display_animate_(((x, y), (w, h)), True, False)
                    continue

                elif name == "SpaceCenter":
                    spaceCenter = OpenSpaceCenter(font)
                    spaceCenter.setPointSize(windowData["pointSize"])
                    spaceCenter.setPre(windowData["pre"])
                    spaceCenter.setAfter(windowData["after"])
                    spaceCenter.set(windowData["input"])

                    window = CurrentSpaceCenterWindow()
                    window.w.getNSWindow().setFrame_display_animate_(((x, y), (w, h)), True, False)
                    continue

            window.setFrame_display_animate_(((x, y), (w, h)), True, False)

    for windowData in project["toolWindows"]:
        name = windowData["windowName"]
        x, y, w, h = windowData["frame"]

        if name == "DebugWindow":
            window = OutputWindow()
            window.show()
            window.w.getNSWindow().setFrame_display_animate_(((x, y), (w, h)), True, False)

        elif name == "InspectorWindow":
            try:
                # a little bit hacky
                # will move to mojo.UI in the upcoming releases
                window = delegate._inspectorWindow.w.getNSWindow()
            except:
                window = None
            if window is None:
                delegate.openInspector_(None)
                window = delegate._inspectorWindow.w.getNSWindow()
            window.setFrame_display_animate_(((x, y), (w, h)), True, False)

    if "execute" in project:
        try:
            ScriptRunner(text=project["execute"])
        except:
            import traceback
            print traceback.format_exc(5)


class SaveRoboFontProject(object):

    def __init__(self):
        w, h = 550, 250
        self.view = vanilla.Group((0, 0, w, h))
        self.view.relative = vanilla.CheckBox((0, 3, 300, 22), "Use Relative Paths")
        self.view.info = vanilla.TextBox((0, 33, 300, 22), "Execute on load:")
        self.view.editor = CodeEditor((0, 60, w, h-70))

        view = self.view.getNSView()
        view.setFrame_(((0, 0), (w, h)))

        path = dialogs.putFile("Save RoboFont Project..", fileTypes=["roboFontProject"], accessoryView=view)

        if path:
            data = self.getData(path)

            writePlist(data, path)

            icon = NSImage.alloc().initByReferencingFile_(os.path.join(os.path.dirname(__file__), "roboFontProjectIcon.png"))
            ws = NSWorkspace.sharedWorkspace()
            ws.setIcon_forFile_options_(icon, path, 0)

    def getData(self, path):
        toolWindows = list()
        documents = dict()
        untitled = list()

        relativePaths = self.view.relative.get()

        for document in NSApp().orderedDocuments():
            url = document.fileURL()
            fileName = None
            if url:
                fileName = url.path()
                if relativePaths and path:
                    fileName = os.path.relpath(fileName, os.path.dirname(path))
                if fileName not in documents:
                    documents[fileName] = []

            for windowController in document.windowControllers():
                window = windowController.window()
                (x, y), (w, h) =  window.frame()
                data = dict()
                data["frame"] = x, y, w, h
                data["windowName"] = window.windowName()

                vanillaWrapper = None
                if hasattr(window.delegate(), "vanillaWrapper"):
                    vanillaWrapper = window.delegate().vanillaWrapper()

                if vanillaWrapper:
                    if data["windowName"] == "GlyphWindow":
                        data["glyphName"] = vanillaWrapper.getGlyph().name
                    elif data["windowName"] == "SpaceCenter":
                            spaceCenter = vanillaWrapper.getSpaceCenter()
                            data["input"] = spaceCenter.get()
                            data["pre"] = spaceCenter.getPre()
                            data["after"] = spaceCenter.getAfter()
                            data["pointSize"] = spaceCenter.getPointSize()

                if fileName:
                    documents[fileName].append(data)
                else:
                    untitled.append(data)

        for window in NSApp().windows():
            if hasattr(window, "windowName"):
                if window.windowName() in ["DebugWindow", "InspectorWindow"]:
                    (x, y), (w, h) =  window.frame()
                    data = dict()
                    data["frame"] = x, y, w, h
                    data["windowName"] = window.windowName()
                    toolWindows.append(data)

        documents["untitled"] = untitled
        info = dict(toolWindows=toolWindows, documents=documents)
        code = self.view.editor.get()
        if code:
            info["execute"] = code
        return info



# file handler

class ReadRoboFontProjectFile(object):

    def __init__(self):
        addObserver(self, "applicationOpenFile", "applicationOpenFile")

    def applicationOpenFile(self, notification):
        path = notification["path"]
        ext = notification["ext"]
        fileHandler = notification["fileHandler"]
        if ext.lower() == ".robofontproject":
            try:
                OpenRoboFontProject(path)
            except:
                import traceback
                print traceback.format_exc(5)
            fileHandler["opened"] = True

ReadRoboFontProjectFile()


# add to menu

class RoboFontProjectMenu(object):

    def __init__(self):
        title = "Save Project..."
        mainMenu = NSApp().mainMenu()
        fileMenu = mainMenu.itemWithTitle_("File")

        if not fileMenu:
            return

        fileMenu = fileMenu.submenu()

        if fileMenu.itemWithTitle_(title):
            return

        index = fileMenu.indexOfItemWithTitle_("Revert to Saved")
        self.target = CallbackWrapper(self.callback)

        newItem = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(title, "action:", "")
        newItem.setTarget_(self.target)

        fileMenu.insertItem_atIndex_(newItem, index+1)

    def callback(self, sender):
        SaveRoboFontProject()

RoboFontProjectMenu()

