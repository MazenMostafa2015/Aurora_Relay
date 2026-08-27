#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Mock-Revit execution test for PyZeada.

The current PyZeada architecture intentionally has no pyzeada_core.py. In
that mode this harness imports and calls every public function in every
pushbutton script. If a legacy core is present, it also imports and calls its
public functions. Transactions are tracked and must close with Commit or
RollBack after Start.
"""
from __future__ import print_function

import importlib.util
import inspect
import os
import sys
import types
import builtins
import ast
import re

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
EXT = os.path.join(ROOT, "PyZeada.extension")
TAB = os.path.join(EXT, "PyZeada.tab")


class Dummy(object):
    def __init__(self, *args, **kwargs):
        self.Id = DummyId(1)
        self.Name = "MockElement"
        self.PathName = ""
        self.IsTemplate = False
        self.CanBePrinted = True
        self.Elevation = 0.0

    def __getattr__(self, name):
        return Dummy()

    def __call__(self, *args, **kwargs):
        return Dummy()

    def __iter__(self):
        return iter([])

    def __len__(self):
        return 0

    def __getitem__(self, key):
        return Dummy()

    def __bool__(self):
        return False

    __nonzero__ = __bool__

    def __int__(self):
        return 0

    def __str__(self):
        return "MockElement"


class DummyId(Dummy):
    InvalidElementId = None

    def __init__(self, value=1):
        self.IntegerValue = value

    def __hash__(self):
        return hash(self.IntegerValue)

    def __eq__(self, other):
        return isinstance(other, DummyId) and self.IntegerValue == other.IntegerValue


class ApiMeta(type):
    def __getattr__(cls, name):
        def factory(*args, **kwargs):
            return Dummy()
        return factory


class ApiType(Dummy, metaclass=ApiMeta):
    pass


class Collector(Dummy):
    def ToElements(self):
        return []

    def ToElementIds(self):
        return []

    def OfCategory(self, *args):
        return self

    def OfClass(self, *args):
        return self

    def WhereElementIsNotElementType(self):
        return self

    def WhereElementIsElementType(self):
        return self


class Transaction(Dummy):
    active = []
    starts = 0
    commits = 0
    rollbacks = 0
    invalid_events = []
    events = []

    def __init__(self, *args, **kwargs):
        Dummy.__init__(self, *args, **kwargs)
        self.started = False

    def Start(self):
        if self.started:
            Transaction.invalid_events.append("duplicate Start")
        self.started = True
        Transaction.starts += 1
        Transaction.events.append("Start")
        Transaction.active.append(self)

    def Commit(self):
        if not self.started:
            Transaction.invalid_events.append("Commit before Start")
        elif self not in Transaction.active:
            Transaction.invalid_events.append("Commit after close")
        else:
            Transaction.active.remove(self)
        self.started = False
        Transaction.events.append("Commit")
        Transaction.commits += 1

    def RollBack(self):
        if not self.started:
            Transaction.invalid_events.append("RollBack before Start")
        elif self not in Transaction.active:
            Transaction.invalid_events.append("RollBack after close")
        else:
            Transaction.active.remove(self)
        self.started = False
        Transaction.events.append("RollBack")
        Transaction.rollbacks += 1


class GenericList(list):
    @classmethod
    def __class_getitem__(cls, item):
        return cls


class EnumValue(int):
    def __new__(cls, name):
        value = int.__new__(cls, abs(hash(name)) % 100000 + 1)
        value.name = name
        return value

    def __str__(self):
        return self.name

    def __repr__(self):
        return self.name


class EnumStub(object):
    def __getattr__(self, name):
        return EnumValue(name)


class GenericModule(types.ModuleType):
    def __getattr__(self, name):
        if name == "__all__":
            raise AttributeError(name)
        return ApiType


class ConfigStub(object):
    def get_option(self, name, default=None):
        return default

    def __getattr__(self, name):
        return None


class NetObject(object):
    __slots__ = ()


class NotifyBase(object):
    __slots__ = ()


class ScriptModule(GenericModule):
    def get_logger(self):
        return Dummy()

    def get_config(self, *args, **kwargs):
        return ConfigStub()

    def get_output(self, *args, **kwargs):
        return Dummy()

    def save_config(self, *args, **kwargs):
        return True


class FormsModule(types.ModuleType):
    WPFWindow = ApiType
    Reactive = ApiType

    def __getattr__(self, name):
        if name == "WarningBar":
            class WarningBar(object):
                def __init__(self, *args, **kwargs):
                    self.args = args
                    self.kwargs = kwargs
                def __enter__(self):
                    return self
                def __exit__(self, *args):
                    return False
            return WarningBar
        if name == "SelectFromList":
            return types.SimpleNamespace(show=lambda *args, **kwargs: [])
        return lambda *args, **kwargs: None


def install_mock_runtime():
    clr = types.ModuleType("clr")
    clr.AddReference = lambda *args: None
    sys.modules["clr"] = clr

    db = GenericModule("Autodesk.Revit.DB")
    db.__path__ = []
    db.FilteredElementCollector = Collector
    db.Transaction = Transaction
    db.ElementId = DummyId
    db.BuiltInCategory = EnumStub()
    db.BuiltInParameter = EnumStub()
    db.ViewFamily = EnumStub()
    db.ViewDetailLevel = EnumStub()
    db.DisplayStyle = EnumStub()
    db.ViewFamily.FloorPlan = "FloorPlan"
    db.ViewFamily.CeilingPlan = "CeilingPlan"
    db.Domain = EnumStub()
    db.StorageType = EnumStub()
    db.PrintRange = EnumStub()
    db.SectionType = EnumStub()
    db.ViewDuplicateOption = EnumStub()
    db.StructuralType = EnumStub()
    db.RebarStyle = EnumStub()
    db.RebarHookOrientation = EnumStub()
    db.ElectricalSystemType = EnumStub()
    db.ConnectorProfileType = EnumStub()
    db.ObjectType = EnumStub()
    db.ParameterFilterRuleFactory = ApiType
    for name in (
        "DWGExportOptions", "Duct", "DuctType", "CableTray", "CableTrayType", "Level", "ElectricalSystem",
        "ElevationMarker", "ElevationMarkerType", "ViewPlan", "FamilySymbol",
        "WallFunction", "OverrideGraphicSettings", "Color", "ElementIntersectsElementFilter",
        "View", "ViewSheet", "ElementTransformUtils", "Transform", "CopyPasteOptions",
        "PrintManager", "ViewSet", "ViewSheetSetting", "ViewSchedule", "SectionType",
        "Floor", "FloorType", "CurveLoop", "Line", "XYZ", "Grid", "IntersectionResultArray",
        "MechanicalSystem", "Rebar", "RebarBarType", "Curve", "ViewDrafting", "ViewFamilyType",
        "NavisworksExportOptions", "Element", "Parameter", "Document", "TaskDialog", "Railing", "RailingType", "SpatialElementBoundaryOptions",
    ):
        setattr(db, name, ApiType)
    db.View3D = Dummy
    db.XYZ = ApiType
    db.XYZ.BasisZ = Dummy()
    db.XYZ.BasisX = Dummy()
    db.XYZ.BasisY = Dummy()
    DummyId.InvalidElementId = DummyId(-1)

    sys.modules["Autodesk"] = types.ModuleType("Autodesk")
    sys.modules["Autodesk.Revit"] = types.ModuleType("Autodesk.Revit")
    sys.modules["Autodesk.Revit.DB"] = db
    ui = GenericModule("Autodesk.Revit.UI")
    ui.__path__ = []
    ui.TaskDialog = ApiType
    ui.ExternalEvent = ApiType
    ui.IExternalEventHandler = ApiType
    sys.modules["Autodesk.Revit.UI"] = ui
    selection = types.ModuleType("Autodesk.Revit.UI.Selection")
    selection.ObjectType = EnumStub()
    sys.modules["Autodesk.Revit.UI.Selection"] = selection
    db_structure = GenericModule("Autodesk.Revit.DB.Structure")
    db_structure.StructuralType = db.StructuralType
    sys.modules["Autodesk.Revit.DB.Structure"] = db_structure
    db_arch = GenericModule("Autodesk.Revit.DB.Architecture")
    db_arch.Room = ApiType
    sys.modules["Autodesk.Revit.DB.Architecture"] = db_arch
    db_mech = GenericModule("Autodesk.Revit.DB.Mechanical")
    db_mech.Space = ApiType
    db_mech.MechanicalSystem = db.MechanicalSystem
    sys.modules["Autodesk.Revit.DB.Mechanical"] = db_mech
    db_events = GenericModule("Autodesk.Revit.DB.Events")
    sys.modules["Autodesk.Revit.DB.Events"] = db_events

    generic = GenericModule("System.Collections.Generic")
    generic.__path__ = []
    generic.List = GenericList
    generic.Dictionary = dict
    sys.modules["System"] = types.ModuleType("System")
    sys.modules["System.Collections"] = types.ModuleType("System.Collections")
    sys.modules["System.Collections.Generic"] = generic
    observable = GenericModule("System.Collections.ObjectModel")
    observable.ObservableCollection = list
    sys.modules["System.Collections.ObjectModel"] = observable
    system = sys.modules["System"]
    system.__path__ = []
    system.String = str
    system.Int64 = int
    system.Action = lambda callback: callback
    system.Object = NetObject
    system.Uri = ApiType
    system.EventHandler = ApiType
    system.Windows = GenericModule("System.Windows")
    system.Windows.__path__ = []
    for name in ("ResizeMode", "Thickness", "Visibility", "Window", "WindowStartupLocation"):
        setattr(system.Windows, name, ApiType)
    sys.modules["System.Windows"] = system.Windows
    for sub_name in ("Controls", "Media", "Media.Animation", "Threading", "Shapes"):
        module_name = "System.Windows." + sub_name
        submodule = GenericModule(module_name)
        submodule.__path__ = []
        sys.modules[module_name] = submodule

    doc = Dummy()
    doc.ActiveView = Dummy()
    uidoc = Dummy()
    uidoc.Selection = Dummy()
    uidoc.Selection.GetElementIds = lambda: []
    revit = GenericModule("pyrevit.revit")
    revit.doc = doc
    revit.uidoc = uidoc
    revit.get_selection = lambda: []
    revit.selection = lambda: []
    revit.ui = GenericModule("pyrevit.revit.ui")
    forms = FormsModule("pyrevit.forms")
    pyrevit = GenericModule("pyrevit")
    pyrevit.__path__ = []
    pyrevit.DB = db
    pyrevit.UI = ui
    pyrevit.revit = revit
    pyrevit.forms = forms
    pyrevit.script = ScriptModule("pyrevit.script")
    host_app = Dummy()
    host_app.version = 2025
    pyrevit.HOST_APP = host_app
    pyrevit.EXEC_PARAMS = Dummy()
    pyrevit.framework = GenericModule("pyrevit.framework")
    pyrevit.framework.List = GenericList
    sys.modules["pyrevit"] = pyrevit
    sys.modules["pyrevit.revit"] = revit
    sys.modules["pyrevit.forms"] = forms
    sys.modules["pyrevit.script"] = pyrevit.script
    sys.modules["pyrevit.framework"] = pyrevit.framework
    sys.modules["pyrevit.userconfig"] = GenericModule("pyrevit.userconfig")
    sys.modules["pyrevit.userconfig"].user_config = ConfigStub()
    sys.modules["pyrevit.coreutils"] = GenericModule("pyrevit.coreutils")
    sys.modules["pyrevit.coreutils.ribbon"] = GenericModule("pyrevit.coreutils.ribbon")
    sys.modules["pyrevit.coreutils.ribbon"].ICON_MEDIUM = "ICON_MEDIUM"
    sys.modules["pyrevit.revit.ui"] = revit.ui
    sys.modules["pyrevit.extensions"] = GenericModule("pyrevit.extensions")
    sys.modules["pyrevit.revit.db"] = GenericModule("pyrevit.revit.db")
    sys.modules["pyrevit.revit.db.failure"] = GenericModule("pyrevit.revit.db.failure")
    sys.modules["pyrevit.revit.db.failure"].failure = ApiType
    sys.modules["wpf"] = GenericModule("wpf")
    sys.modules["urllib2"] = GenericModule("urllib2")
    # Optional integrations are deliberately absent. The affected buttons must
    # import cleanly and report their unavailable state rather than crash.
    for optional_name in ("streambim", "streambim.streambim_api", "extensible_storage", "toolbox_probe"):
        sys.modules.pop(optional_name, None)
    component_model = GenericModule("System.ComponentModel")
    component_model.INotifyPropertyChanged = NotifyBase
    sys.modules["System.ComponentModel"] = component_model
    builtins.__revit__ = Dummy()
    builtins.__revit__.ActiveUIDocument = Dummy()
    builtins.__revit__.ActiveUIDocument.Document = doc
    pyrevit.script.get_script_path = lambda: os.path.dirname(__file__)


def script_paths():
    manifest_path = os.path.join(ROOT, "button-manifest.txt")
    if os.path.isfile(manifest_path):
        paths = []
        for line in open(manifest_path, "r"):
            if not line.strip():
                continue
            group, title, action = line.rstrip().split("|")
            if group.startswith("Architecture"):
                panel = "Architecture.panel"
            elif group.startswith("Structure"):
                panel = "Structure.panel"
            elif group.startswith("MEP"):
                panel = "MEP.panel"
            else:
                panel = "General.panel"
            folder = os.path.join(TAB, panel, group, title.replace(" ", "_") + ".pushbutton")
            paths.append(os.path.join(folder, "script.py"))
        return paths
    paths = []
    for current, dirs, files in os.walk(TAB):
        dirs[:] = [item for item in dirs if item != "__pycache__"]
        if current.endswith(".pushbutton") and "script.py" in files:
            paths.append(os.path.join(current, "script.py"))
    return sorted(paths)


def affected_script_paths():
    names = (
        "Create Spaces.pushbutton", "Tag All Spaces.pushbutton", "Colorize.pushbutton",
        "ColorElements.pushbutton", "ChecklistImporter.pushbutton", "BetterSchedule.pushbutton",
        "Clash Views.pushbutton", "Markers.pushbutton",
    )
    result = []
    for current, dirs, files in os.walk(TAB):
        if current.endswith(names) and "script.py" in files:
            result.append(os.path.join(current, "script.py"))
    return sorted(result)


def load_module(path, index):
    name = "pyzeada_mock_%s" % index
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def call_public_functions(module, label):
    failures = []
    called = []
    for name, function in inspect.getmembers(module, inspect.isfunction):
        if name.startswith("_") or getattr(function, "__module__", None) != module.__name__:
            continue
        try:
            signature = inspect.signature(function)
            args = []
            for parameter in signature.parameters.values():
                if parameter.kind in (parameter.VAR_POSITIONAL, parameter.VAR_KEYWORD):
                    continue
                if parameter.default is parameter.empty:
                    args.append(Dummy())
            function(*args)
            called.append(name)
        except Exception as error:
            failures.append("%s.%s: %s" % (label, name, error))
    return called, failures


def audit_source_contracts(paths):
    failures = []
    forbidden = (
        ("nonlocal", re.compile(r"\bnonlocal\b")),
        ("async", re.compile(r"\basync\b")),
        ("await", re.compile(r"\bawait\b")),
        ("f-string", re.compile(r"(^|[^A-Za-z0-9_])f(?:\"|')")),
        ("pathlib", re.compile(r"\bpathlib\b")),
        ("dataclasses", re.compile(r"\bdataclasses\b")),
    )
    bad_db_names = {"ObjectType", "StructuralType", "MechanicalSystem", "ElevationMarkerType"}
    for path in paths:
        source = open(path, "r", encoding="utf-8", errors="replace").read()
        for number, line in enumerate(source.splitlines(), 1):
            for label, pattern in forbidden:
                if pattern.search(line):
                    failures.append("%s:%d: forbidden %s" % (os.path.relpath(path, ROOT), number, label))
        try:
            tree = ast.parse(source, filename=path)
        except SyntaxError as error:
            failures.append("%s:%d: syntax error: %s" % (os.path.relpath(path, ROOT), error.lineno, error.msg))
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module == "Autodesk.Revit.DB":
                for alias in node.names:
                    if alias.name in bad_db_names:
                        failures.append("%s:%d: invalid DB namespace import %s" % (os.path.relpath(path, ROOT), node.lineno, alias.name))
    return failures


def audit_transaction_events(events):
    stack = []
    failures = []
    for index, event in enumerate(events):
        if event == "Start":
            stack.append(index)
        elif event in ("Commit", "RollBack"):
            if not stack:
                failures.append("%s before Start at event %d" % (event, index))
            else:
                stack.pop()
    if stack:
        failures.append("%d Start event(s) lack Commit/RollBack" % len(stack))
    return failures


def legacy_core_path():
    candidate = os.path.join(EXT, "lib", "pyzeada_core.py")
    return candidate if os.path.isfile(candidate) else None


def main():
    install_mock_runtime()
    core_dir = os.path.join(EXT, "lib")
    if core_dir not in sys.path:
        sys.path.insert(0, core_dir)
    paths = script_paths()
    if not paths:
        print("FAIL: no PyZeada pushbutton scripts found")
        return 1

    failures = []
    total_functions = 0
    failures.extend(audit_source_contracts(sorted(set(paths + affected_script_paths()))))

    core = legacy_core_path()
    if core:
        module = load_module(core, "core")
        called, errors = call_public_functions(module, "pyzeada_core")
        total_functions += len(called)
        failures.extend(errors)
        print("Legacy core functions called: %d" % len(called))
    else:
        print("No shared pyzeada_core.py found; testing self-contained entry scripts instead.")

    for index, path in enumerate(paths):
        label = os.path.relpath(path, ROOT)
        try:
            module = load_module(path, index)
            called, errors = call_public_functions(module, label)
            wrapper_called = []
            for name, function in inspect.getmembers(module, inspect.isfunction):
                if name.startswith("_") or getattr(function, "__module__", None) != "pyzeada_core":
                    continue
                try:
                    function()
                    wrapper_called.append(name)
                except Exception as error:
                    errors.append("%s.%s: wrapper-bound core call failed: %s" % (label, name, error))
            total_functions += len(called) + len(wrapper_called)
            failures.extend(errors)
            if not called and not wrapper_called:
                failures.append("%s: no callable entry point" % label)
        except Exception as error:
            failures.append("%s: import failed: %s" % (label, error))

    # Import affected non-canonical scripts with optional integrations absent.
    for offset, path in enumerate(affected_script_paths(), len(paths) + 1000):
        label = os.path.relpath(path, ROOT)
        try:
            module = load_module(path, offset)
            if label.endswith("ChecklistImporter.pushbutton/script.py") and getattr(module, "_STREAMBIM_AVAILABLE", True):
                failures.append("%s: optional StreamBIM integration was not absent/guarded" % label)
            if label.endswith("BetterSchedule.pushbutton/script.py") and getattr(module, "find_better_schedule_script", "missing") is not None:
                failures.append("%s: absent toolbox_probe did not enter graceful fallback" % label)
        except Exception as error:
            failures.append("%s: affected-button import failed: %s" % (label, error))

    execution_failures = list(failures)
    transaction_failures = []
    if Transaction.active:
        transaction_failures.append("%d transaction(s) started without Commit or RollBack" % len(Transaction.active))
    transaction_failures.extend(Transaction.invalid_events)
    transaction_failures.extend(audit_transaction_events(Transaction.events))
    all_failures = execution_failures + transaction_failures
    print("Mock-Revit scope: scripts=%d public_functions=%d" % (len(paths), total_functions))
    print("Affected optional-import scripts checked: %d" % len(affected_script_paths()))
    print("Transactions: starts=%d commits=%d rollbacks=%d" % (
        Transaction.starts, Transaction.commits, Transaction.rollbacks
    ))
    if execution_failures:
        print("[FAIL] Mock-Revit imports and public-function execution (%d finding(s))" % len(execution_failures))
        for failure in execution_failures:
            print("  - %s" % failure)
    else:
        print("[PASS] Mock-Revit imports and public-function execution")
    if transaction_failures:
        print("[FAIL] Transaction pairing (%d finding(s))" % len(transaction_failures))
        for failure in transaction_failures:
            print("  - %s" % failure)
    else:
        print("[PASS] Transaction Start/Commit/RollBack pairing")
    if all_failures:
        print("FAIL: mock-Revit execution findings: %d" % len(all_failures))
        return 1
    print("PASS: mock-Revit imports, public-function calls, optional dependency fallbacks, and transaction closure checks completed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
