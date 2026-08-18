# -*- coding: utf-8 -*-
"""Aurora Relay allow-listed RevitPythonShell operations.

Load this module from RevitPythonShell only after the local Aurora Relay bridge
has verified a user-owned, confirmed operation. These functions deliberately do
not execute arbitrary Python supplied by a connector request.
"""
from __future__ import print_function

from Autodesk.Revit.DB import ElementId, FilteredElementCollector, FamilySymbol, Level, Transaction, XYZ
from Autodesk.Revit.DB.Structure import StructuralType


def set_parameter(doc, element_id, parameter_name, value, transaction_name):
    """Set an existing writable parameter inside a single named transaction."""
    element = doc.GetElement(ElementId(int(element_id)))
    if element is None:
        raise ValueError("Element {0} was not found".format(element_id))
    parameter = element.LookupParameter(parameter_name)
    if parameter is None or parameter.IsReadOnly:
        raise ValueError("Parameter '{0}' is unavailable or read-only".format(parameter_name))
    tx = Transaction(doc, transaction_name)
    tx.Start()
    try:
        if parameter.StorageType.ToString() == "String":
            parameter.Set(str(value))
        elif parameter.StorageType.ToString() == "Integer":
            parameter.Set(int(value))
        elif parameter.StorageType.ToString() == "Double":
            parameter.Set(float(value))
        else:
            raise ValueError("Unsupported parameter storage type: {0}".format(parameter.StorageType))
        tx.Commit()
    except Exception:
        tx.RollBack()
        raise
    return {"element_id": int(element_id), "parameter": parameter_name, "value": value}


def place_family_instance(doc, family_symbol_name, level_name, x, y, z, transaction_name, parameters=None):
    """Place a point-based family instance on an existing level by exact name."""
    symbol = next((item for item in FilteredElementCollector(doc).OfClass(FamilySymbol) if item.Family.Name == family_symbol_name or item.Name == family_symbol_name), None)
    if symbol is None:
        raise ValueError("Family symbol '{0}' was not found".format(family_symbol_name))
    level = next((item for item in FilteredElementCollector(doc).OfClass(Level) if item.Name == level_name), None)
    if level is None:
        raise ValueError("Level '{0}' was not found".format(level_name))
    tx = Transaction(doc, transaction_name)
    tx.Start()
    try:
        if not symbol.IsActive:
            symbol.Activate()
            doc.Regenerate()
        instance = doc.Create.NewFamilyInstance(XYZ(float(x), float(y), float(z)), symbol, level, StructuralType.NonStructural)
        for name, value in (parameters or {}).items():
            parameter = instance.LookupParameter(name)
            if parameter is None or parameter.IsReadOnly:
                raise ValueError("Instance parameter '{0}' is unavailable or read-only".format(name))
            parameter.Set(str(value))
        tx.Commit()
    except Exception:
        tx.RollBack()
        raise
    return {"element_id": instance.Id.IntegerValue, "family_symbol": family_symbol_name, "level": level_name}
