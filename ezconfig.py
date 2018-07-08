from enum import Enum
import numpy as np

class ConfigFile(object):
    def __init__(self, filepath=None):
        self.fields = {}
        self.paths = []

        if filepath is not None:
            self.load(filepath)

    def load(self, filepath, overwrite=False, reload=False, virtual=False): # set reload when you want to reload all fields
        """
        Load config file from filepath.
        :param filepath: path to config
        :type filepath: str
        :param overwrite: overwrite existing fields
        :type overwrite: bool
        :param reload: reload the whole config class (deletes all fields present before loading)
        :type reload: bool
        :param virtual: if set True, when saving this config, none of the loaded fields is saved. Parameter virtual serves
        as a way to add useful values to the config that we don't want to save
        :type virtual: bool
        :return: nothing
        :rtype:
        """
        self.paths.append(filepath)
        if reload: self.fields = {}
        with open(filepath, 'r') as f:
            lines = f.readlines()
            for line in lines:
                line_nospace = line.replace(' ','').replace('\t','')
                if line_nospace == '\n' or line_nospace.startswith('#'): continue # ignore empty lines or commented lines
                field = ConfigField(line.replace('\n',''), virtual)
                if field.name not in self.fields or overwrite: # set overwrite when you want to allow overwriting fields
                    self.fields[field.name] = field
                else:
                    raise KeyError('The field {} is duplicate.'.format(field.name))

    def save(self, filepath):
        with open(filepath, 'w') as f:
            f.writelines([str(field)+'\n' for _,field in self.fields.items() if not field.virtual])

    def merge_with(self, config_file, overwrite=True):
        for name,field in config_file.fields.items():
            if self.contains_field(name) and not overwrite:
                raise KeyError('The field {} is already present. Set overwrite=True to overwrite all duplicates.'.format(field.name))

            self.fields[name] = field

    def contains_field(self, name):
        return name in self.fields

    def contains(self, name):
        return self.contains_field(name)

    # set field with a completely new string
    def set_field_from_string(self, fieldstring):
        field = ConfigField(fieldstring.replace('\n',''))
        if field.name not in self.fields:
            raise KeyError('The field {} is not present.'.format(field.name))
        field_current = self.fields[field.name]
        if field.dtype is not field_current.dtype:
            raise KeyError('The data types are mismatching in the field {}. The setting field '
                           'has dtype {} while the current one {}.'\
                           .format(field.name, field.dtype, field_current.dtype))
        self.fields[field.name] = field

    def add_field_from_string(self, fieldstring, virtual=False):
        field = ConfigField(fieldstring.replace('\n',''), virtual)
        if field.name in self.fields:
            raise KeyError('The field {} is already present. Use set_field_from_string to overwrite it.'.format(field.name))
        self.fields[field.name] = field

    # set value of a field
    def set_value(self, field_name, value):
        if field_name not in self.fields:
            raise KeyError('The field {} is not present.'.format(field_name))
        field = self.fields[field_name]
        field.dtype.check_type_error(value)
        field.value = value

    def _get(self, name, dtype): # get field, checks if key is present and also given data type
        if name not in self.fields:
            raise KeyError('The field {} is not present.'.format(name))
        field = self.fields[name]
        if field.dtype is not dtype:
            raise TypeError('The field {} is not of type {} but of type {}'.format(name, dtype, field.dtype))
        field.used = True
        return field.value

    def get_float(self, name): return self._get(name, ConfigFieldDtype.Float)
    def get_int(self, name): return self._get(name, ConfigFieldDtype.Int)
    def get_string(self, name): return self._get(name, ConfigFieldDtype.String)
    def get_bool(self, name): return self._get(name, ConfigFieldDtype.Bool)
    def try_float(self, name): return self.get_float(name) if self.contains_field(name) else None
    def try_int(self, name): return self.get_int(name) if self.contains_field(name) else None
    def try_bool(self, name): return self.contains_field(name) and self.get_bool(name)

    def add_field(self, name, dtype, value, virtual=False, comment=''): # virtual fields don't get saved to files
        if name in self.fields:
            raise KeyError('The field {} is already present.'.format(name))
        field = ConfigField(virtual=virtual).init(name, dtype, value, comment)
        self.fields[name] = field

    def add_float(self, name, value, virtual=False, comment=''): self.add_field(name, ConfigFieldDtype.Float, value, virtual, comment)
    def add_int(self, name, value, virtual=False, comment=''): self.add_field(name, ConfigFieldDtype.Int, value, virtual, comment)
    def add_string(self, name, value, virtual=False, comment=''): self.add_field(name, ConfigFieldDtype.String, value, virtual, comment)
    def add_bool(self, name, value, virtual=False, comment=''): self.add_field(name, ConfigFieldDtype.Bool, value, virtual, comment)

    def check_unused(self): # checks if some fields were not used, can help to detect forgotten implementations of some parameters
        for _,field in self.fields.items():
            if not field.used:
                print('WARNING: config field {} was not used once.'.format(field.name))

    def print(self):
        print('-' * 60)
        print('ConfigFile loaded from paths:')
        for path in self.paths:
            print('   ' + path)

        print('-' * 60)
        max_name_len = 0
        max_value_len = 0
        for name in self.fields.keys(): max_name_len = max(max_name_len, len(name))
        for value in [field.value for field in self.fields.values()]: max_value_len = max(max_value_len, len(str(value)))
        row_format = '{{:<{}}}{{:<{}}}'.format(max_name_len+2, max_value_len+2) +  '{:<15}' * 2
        print(row_format.format('Field Name', 'Value', 'Data Type', 'Is Virtual'))
        for _,field in self.fields.items():
            print(row_format.format(field.name, field.value, field.dtype.value, field.virtual))
        print('-' * 60)



class ConfigField(object):
    def __init__(self, parsestring=None, virtual=False): # virtual property decides whether the field is saved into file
        self.value_parser = ConfigValueParser()
        self.virtual = virtual
        self.used = False
        self.comment = ''
        if parsestring is not None:
            self.parse(parsestring)

    def init(self, name, dtype, value, comment=''):
        self.name = name
        self.dtype = dtype
        self.value = value
        self.comment = comment
        dtype.check_type_error(value)
        return self

    def parse(self, parsestring):
        parts = parsestring.split(';')
        assert len(parts) >= 3, print('each config field string has to have 3 parts. [{}]'.format(parsestring))
        self.name = parts[0]
        self.dtype = ConfigFieldDtype(parts[1])
        split = parts[2].split('#')
        if len(split) > 1:
            self.comment = split[1]
        parts[2] = split[0]
        self.value = self.value_parser.parse_value(self.dtype, parts[2])

    def __str__(self):
        return (self.name + ';' + self.dtype.value + ';' + str(self.value) + '#' + self.comment)


class ConfigFieldDtype(Enum):
    Bool = 'bool'
    Float = 'float'
    Int = 'int'
    String = 'string'

    def check_type(self, value):
        if value is None: return True # return None
        if self.value == 'bool': return isinstance(value, bool)
        if self.value == 'float': return isinstance(value, float)
        if self.value == 'int': return isinstance(value, int)
        if self.value == 'string': return isinstance(value, str)
        raise NotImplementedError('this type is not implemented')

    def check_type_error(self, value):
        if self.value == 'bool':
            if not isinstance(value, bool): raise TypeError('The value "{}" is not of type bool.'.format(value))
        if self.value == 'float':
            if not isinstance(value, float): raise TypeError('The value "{}" is not of type float.'.format(value))
        if self.value == 'int':
            if not isinstance(value, int): raise TypeError('The value "{}" is not of type int.'.format(value))
        if self.value == 'string':
            if not isinstance(value, str): raise TypeError('The value "{}" is not of type string.'.format(value))

def parse_bool(valuestring):
    if valuestring.lower() in ['true', '1'] :
        return True
    elif valuestring.lower() in ['false', '0'] :
        return False
    else:
        raise ValueError('Could not parse value "{}" as bool'.format(valuestring))

class ConfigValueParser(object):
    def __init__(self):
        self.functions = [LogUniform(), Uniform(), RandomBool()]

    def parse_value(self, dtype, valuestring):
        valuestring2 = valuestring.replace(' ','').replace('\t','')
        fun_value = self._check_functions(dtype, valuestring2)
        if dtype is ConfigFieldDtype.String: # return plain string
            return valuestring
        elif fun_value is not None: # return function value if found
            return fun_value

        if valuestring2 == 'None':
            return None
        # in the rest of the cases simply try to parse the string as given datatype
        if dtype is ConfigFieldDtype.Bool:
            return parse_bool(valuestring2) # have to use proprietary func as python built-in parses all non-empty strings as true
        elif dtype is ConfigFieldDtype.Int:
            return int(valuestring2)
        elif dtype is ConfigFieldDtype.Float:
            return float(valuestring2)
        else:
            raise NotImplementedError('Dtype {} has not been implemented'.format(dtype))

    def _check_functions(self, dtype, valuestring):
        for function in self.functions:
            if function.is_instance(valuestring):
                return function.parsevalue(dtype, valuestring)

        return None


class ConfigFunction(object):
    def __init__(self, name):
        self.name = name

    def parsevalue(self, dtype, valuestring):
        """
        Returns value generated according to parsestring function definition
        :param dtype:
        :type dtype:
        :param parsestring:
        :type parsestring:
        :return:
        :rtype:
        """
        pass

    def is_instance(self, valuestring):
        """
        Returns true if parsestring represents instance of this function
        :param parsestring:
        :type parsestring: string
        :return:
        :rtype: bool
        """
        return valuestring.startswith(self.name + '(')


class LogUniform(ConfigFunction):
    def __init__(self):
        ConfigFunction.__init__(self, 'LogUniform')

    def parsevalue(self, dtype, valuestring):
        if dtype is ConfigFieldDtype.Float:
            values = valuestring.replace('LogUniform(','').replace(')','').split(',')
            a = float(values[0])
            b = float(values[1])
            value = float(np.exp(np.random.uniform(np.log(a), np.log(b))))
            return value
        else:
            raise TypeError('LogUniform function does not support type {}'.format(dtype))

class Uniform(ConfigFunction):
    def __init__(self):
        ConfigFunction.__init__(self, 'Uniform')

    def parsevalue(self, dtype, valuestring):
        if dtype is ConfigFieldDtype.Float:
            values = valuestring.replace('Uniform(','').replace(')','').split(',')
            a = float(values[0])
            b = float(values[1])
            value = float(np.random.uniform(a,b))
            return value
        elif dtype is ConfigFieldDtype.Int: # uniform for int is inclusive of both points
            values = valuestring.replace('Uniform(','').replace(')','').split(',')
            a = int(values[0])
            b = int(values[1])
            value = int(np.random.choice(np.arange(a,b+1)))
            return value
        else:
            raise TypeError('Uniform function does not support type {}'.format(dtype))

class RandomBool(ConfigFunction):
    def __init__(self):
        ConfigFunction.__init__(self, 'RandomBool')

    def parsevalue(self, dtype, valuestring):
        if dtype is ConfigFieldDtype.Bool:
            p_true = float(valuestring.replace('RandomBool(','').replace(')',''))
            return np.random.rand() < p_true
        else:
            raise TypeError('RandomBool function does not support type {}'.format(dtype))

if __name__ == '__main__':

    dtype = ConfigFieldDtype.Bool
    print(dtype.value)

    ConfigFile('configtest.txt').save('configtest2.txt')