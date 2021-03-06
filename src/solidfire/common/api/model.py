
import json

KNOWN_CONVERSIONS = {
    type(set): list
}

def serialize(val):
    if hasattr(val, 'to_json'):
        return val.to_json()
    elif type(val) in KNOWN_CONVERSIONS:
        return KNOWN_CONVERSIONS[type(val)](val)
    elif isinstance(val, dict):
        return dict((k, serialize(v)) for k, v in val.items())
    else:
        return val

def extract(typ, src):
    if hasattr(typ, 'extract'):
        return typ.extract(src)
    else:
        return src

class ModelPropery(object):
    def __init__(self, member_name, member_type, array=False, optional=False, documentation=None):
        self._member_name = member_name
        self._member_type = member_type
        self._array = array
        self._optional = optional
        self._documentation = documentation

    def extend_json(self, out, data):
        if data is None:
            if not self._optional:
                out[self._member_name] = None
        elif self._array:
            out[self._member_name] = [serialize(x) for x in data]
        else:
            out[self._member_name] = serialize(data)

    def extract_from(self, data):
        if self._array:
            return [] if data is None else [extract(self._member_type, x) for x in data]
        else:
            return extract(self._member_type, data)

class MetaDataObject(type):
    def __init__(cls, name, bases, classdict):
        super(MetaDataObject, cls).__init__(name, bases, classdict)
        cls._create_properties()

class DataObject(metaclass=MetaDataObject):
    _properties = None

    @classmethod
    def _create_properties(cls):
        cls._properties = {}
        for name in dir(cls):
            prop = getattr(cls, name, None)
            if isinstance(prop, ModelPropery):
                cls._properties[name] = prop

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            if k not in type(self)._properties:
                raise TypeError(str.format('Key "{k}" is not a valid property', k=k))
            else:
                setattr(self, k, v)

    def __repr__(self):
        props = []
        for name, prop in sorted(type(self)._properties.items()):
            if prop._array:
                r = str.format('[{vals}]', vals=str.join(', ', (repr(x) for x in getattr(self, name))))
            else:
                r = repr(getattr(self, name))
            props.append(str.format('{name}={repr}', name=name, repr=r))
        return str.format('{cls}({props})', cls=type(self).__name__, props=str.join(', ', props))

    def to_json(self):
        out = {}
        for name, prop in type(self)._properties.items():
            prop.extend_json(out, getattr(self, name, None))
        return out

    @classmethod
    def extract(cls, data, strict=True):
        ctor_dict = {}
        for name, prop in cls._properties.items():
            if prop._member_name in data:
                ctor_dict[name] = prop.extract_from(data[prop._member_name])
            elif prop._optional:
                ctor_dict[name] = None
            elif prop._array:
                ctor_dict[name] = []
            elif not strict:
                ctor_dict[name] = None
            else:
                raise TypeError(str.format('Can not create {typ}: missing required propery "{name}" in {input}',
                                           typ=cls.__name__,
                                           name=prop._member_name,
                                           input=json.dumps(data)
                                           )
                                )
        return cls(**ctor_dict)

def property(member_name, member_type, array=False, optional=False, documentation=None):
    documentation = documentation or str.format('Propery of type {typ}{arr}',
                                                typ=member_type,
                                                arr=('[]' if array else '')
                                                )
    typ = type(member_name + 'Property', (ModelPropery,), { '__doc__': documentation })
    return typ(member_name=member_name,
               member_type=member_type,
               array=array,
               optional=optional,
               documentation=documentation
               )
