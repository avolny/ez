import pprint
from collections import OrderedDict
from ezconfig import ConfigFile
import inspect

class JsonIndex(object):
    def __init__(self, json, reset=True):
        self.indices = [] # scope
        # self.types = []
        self.json = json
        if reset:
            self.reset()

    def reset(self):
        self.indices = []
        if isinstance(self.json, OrderedDict) and len(self.json) > 0:
            self.indices.append(list(self.json.keys())[0])
        elif isinstance(self.json, list) and len(self.json) > 0:
            self.indices.append(0)

    # def _sync_types(self):
    #     o = self.json
    #     self.types = []
    #     for ix in self.indices:
    #         self.types.append(type())

    def get_value(self):
        o = self.json
        for ix in self.indices:
            o = o[ix]
            # print(o)
        return o

    def copy(self):
        index = JsonIndex(self.json, reset=False)
        index.indices = self.indices

    def is_head_dict(self):
        return isinstance(self.get_value(), OrderedDict)

    def is_head_list(self):
        return isinstance(self.get_value(), list)
        
    def deeper(self, index):
        # ix = self.copy()
        self.indices.append(index)

    def higher(self):
        return self.indices.pop(-1)

    def first_index(self):
        return self.indices[0]

    def __len__(self):
        return len(self.indices)

    def depth(self):
        return len(self)


class JsonPrinter(object):
    def __init__(self, ncols=80, nindents=2, nlistcollapse=6, ndictcollapse=10):
        self.ncols = ncols
        self.nindents = nindents
        self.nlistcollapse = nlistcollapse
        self.ndictcollapse = ndictcollapse

    def jprint(self, json):
        print(self.jstr(json))

    def jstr(self, json):
        return self._jstr(json, 0, self.ncols)

    def _jstr(self, json, indent=0, remaining=0):
        t = ' '*indent
        nl = '\n'
        if isinstance(json, list):
            s = '['
            if len(json) > 0: s += nl + t
            for i,val in enumerate(json):
                s += self._jstr(val, indent+self.nindents)
                if i < len(json)-1:
                    s += ',' + nl + t
            if len(json) > 0: s += nl + t
            s += ']'
        elif isinstance(json, dict) or isinstance(json, OrderedDict):
            s = '{'
            if len(json) > 0: s += nl + t
            for i,(key, val) in enumerate(list(json.items())):
                s += str(key) + ': ' + self._jstr(val, indent+self.nindents)
                if i < len(json)-1:
                    s += ',' + nl + t
            if len(json) > 0: s += nl + t
            s += '}'
        else:
            s = str(json)
        return s


class FastPrint(object):
    def __init__(self, configpath='.fastprint_config.txt'):
        self.json = OrderedDict({"print": OrderedDict(), "calls": OrderedDict()})
        self.index = JsonIndex(self.json)
        self.configfile = self._get_config(configpath)
        self.counter = 0

    def config(self, **kwargs):
        for key,val in kwargs.items():
            if not self.configfile.contains(key):
                raise ValueError('key {} is not present in config fields'.format(key))
            self.configfile.set_value(key, val)

    def _get_config(self, path):
        # method that searches the pwd for
        import os
        if os.path.exists(path):
            return ConfigFile(path)
        else: # default config
            print('Creating new config file with default settings, .fastprint_config.txt')
            config = ConfigFile()
            ### TO DO: defaults,
            # config.add_bool('use_class_wrappers', True, comment='set false when you want to deactivate all class wrappers')
            config.add_bool('use_function_wrappers', True, comment='set false when you want to deactivate all function '
                                                                   'wrappers (including the ones from class wrappers)')
            config.add_bool('print_fn_args', True, comment='set false when you don\'t want to print arguments for each function call')
            config.add_bool('print_fn_retval', True, comment='set false when you don\' want to print returned value for each fn call')
            config.add_int('max_depth', 10, comment='Set the maximum print depth')
            config.add_bool('simple', False, comment='Set true when you want simple function print omitting args and retvals')
            config.save(path)
            return config

    # def
    def _next_counter(self):
        self.counter += 1
        return str(self.counter-1).zfill(3)

    def __str__(self):
        jp = JsonPrinter()
        return jp.jstr(self.json)
        # pp = pprint.PrettyPrinter(indent=4, width=80)
        # pp.pprint(self.json)

    def _construct_args_dict(self, argspec, fargs, fkwargs):
        # arguments consistency does not need to be checked
        # because python raises exception on calls with invalid
        # arguments implicitly
        args, varargs, varkw, defaults = argspec[:4]
        defaults = defaults if defaults is not None else []
        di = len(args) - len(defaults)

        # initialize dict with argument names and values (default if not provided)
        d = {key:fargs[i] if i < len(fargs) else # unnamed function arguments
                 fkwargs[key] if (key in fkwargs.keys()) else # keyword arguments
                 defaults[i - di] if i >= di else# default values otherwise
                 'ParameterNotDefined-Error, please report'
                 for i,key in enumerate(args)}

        # fill in *args
        if varargs is not None:
            d[varargs] = list(fargs[len(fargs)-len(args):]) if len(fargs)-len(args) > 0 else []

        # fill in **kwargs
        if varkw is not None:
            d[varkw] = {key:val for key,val in fkwargs.items() if key not in args}

        return d


    def __call__(self, *args, **kwargs):
        if len(args) == len(kwargs) == 0: # p() ... print contents of fast print object
            print(self.__str__())
        elif len(args) >= 1 and (callable(args[0]) or isinstance(args[0], type)): # decorator case
            def decorate(func):
                def wrapper(*wargs, **wkwargs):  # function wrapper that replaces the decorated function
                    def entry(*args, **kwargs):
                        self.jump_to_call() # make sure the correct index is in place

                        # inspection for argument names and default values
                        argspec = inspect.getfullargspec(func)  # Works only for python 2.x
                        # put together the actual parameter-value pairs that the function receives
                        argsdict = self._construct_args_dict(argspec, wargs, wkwargs)
                        fname = self._next_counter() + '_' + func.__name__
                        ix = self.add_dict(fname, {})
                        # go deeper into the fname level
                        self.index.deeper(ix)
                        # add dictionary with parameter names and values if not disallowed
                        if not self.configfile.get_bool('simple') and\
                            ('print_fn_args' not in kwargs or kwargs['print_fn_args']) and\
                            self.configfile.get_bool('print_fn_args'):
                            self.add_dict('args', argsdict)

                        if not self.configfile.get_bool('simple'):
                            ix = self.add_dict('calls', {})
                            # go deeper into the "calls" level
                            self.index.deeper(ix)

                    def exit(*args, **kwargs):
                        retval = [args[0]]
                        args = args[1:]

                        if not self.configfile.get_bool('simple'):
                            # get out of the "calls" level
                            self.index.higher()

                        # add dictionary with retvals if not disallowed
                        if  not self.configfile.get_bool('simple') and\
                            ('print_fn_retval' not in kwargs or kwargs['print_fn_retval']) and \
                            self.configfile.get_bool('print_fn_retval'):
                            self.add_dict_record('retval', str(retval))
                        self.index.higher()
                        if len(self.index) == 0:
                            self.index.deeper('print') # return to regular print
                        pass

                    entry(*args, **kwargs)  # call wrappers with outer, decorator arguments
                    retval = func(*wargs, **wkwargs)
                    exit(*([retval] + list(args)), **kwargs)  # call wrappers with outer, decorator arguments
                    return retval

                return wrapper if self.configfile.get_bool('use_function_wrappers') else func
            if isinstance(args[0], type): # class wrapper
                Cls = args[0]
                class NewCls(object):
                    # CODE SOURCE: https://www.codementor.io/sheena/advanced-use-python-decorators-class-function-du107nxsv
                    def __init__(self, *args, **kwargs):
                        self.oInstance = Cls(*args, **kwargs)

                    def __getattribute__(self, s):
                        """
                        this is called whenever any attribute of a NewCls object is accessed. This function first tries to
                        get the attribute off NewCls. If it fails then it tries to fetch the attribute from self.oInstance (an
                        instance of the decorated class). If it manages to fetch the attribute from self.oInstance, and
                        the attribute is an instance method then `time_this` is applied.
                        """
                        try:
                            x = super(NewCls, self).__getattribute__(s)
                        except AttributeError:
                            pass
                        else:
                            return x
                        x = self.oInstance.__getattribute__(s)
                        if type(x) == type(self.__init__):  # it is an instance method
                            return decorate(x)  # this is equivalent of just decorating the method with time_this
                        else:
                            return x

                return NewCls # return wrapped class
            elif callable(args[0]):
                func = args[0]
                return decorate(func)
        elif len(args) == 1 and len(kwargs) == 0: # single non-kw argument
            self.add_record(self._next_counter() + '_' + type(args[0]).__name__, args[0])
        elif len(args) > 1 and isinstance(args[0], str): # if called with first param as string, all other
                                                         # params are treated as str format params
            self.add_record(self._next_counter() + '_' + type(args[0]).__name__, args[0].format(*args[1:],**kwargs))
        elif len(args) == 0 and len(kwargs) >= 1: # single kw arguments
            for key, value in kwargs.items():
                self.add_record(self._next_counter() + '_' + key, value)
            # key, value = list(kwargs.items())[0]
            # self.add_record(key, value)

    def jump_to_call(self):
        if self.index.depth() > 0 and self.index.indices[0] != "calls":
            self.index.indices = ['calls']

    def add_dict(self, key, d, index=None):
        if isinstance(d, dict):
            d = OrderedDict(d)
            return self.add_record(key, d, stringify=False)

    def add_record(self, key, value, index=None, stringify=True):
        if self.index.is_head_dict():
            return self.add_dict_record(key, value, index, stringify)
        elif self.index.is_head_list():
            return self.add_list_record(value, index, stringify)

    def add_dict_record(self, key, value, index=None, stringify=True):
        if index is None:
            index = self.index
        index.get_value()[key] = self._stringify(value) if stringify else value
        return key

    def add_list_record(self, value, index=None, stringify=True):
        if index is None:
            index = self.index
        index.get_value().append(self._stringify(value) if stringify else value)
        return len(index.get_value()) - 1

    def _stringify(self, value, expand=False):
        return str(value)
        # if hasattr(value, '__dict__'): # is object
        #     if type(value).__dict__['__str__'] is not object.__str__:
        #         return str(value)

        # str_op = getattr(self, "__str__", None)
        # if callable(str_op):
        #     if type(value).__dict__['__str__'] is not object.__str__:
        #     invert_op(self.path.parent_op)
        #
        # if type(value).__dict__['__str__'] is not object.__str__:
        # if isinstance(value, object):

ff = FastPrint()


# class A(object):
#     def __init__(self, par1='abc'):
#         self.par1 = par1
#

def example1():
    ff('abcd')
    ff(text='ghij')
    ff('{} + {} = {}',3,5,3+5)
    ff()

def example2():
    @ff
    def add(a, b):
        ff('{} + {} = {}', a, b, a + b)
        return a + b

    @ff
    def multi(a, b):
        sum = 0
        for i in range(b):
            sum = add(sum, a)
        ff('{} * {} = {}', a, b, a * b)
        return sum

    def foo(a, b, c=2, *args, **kwargs):
        ff(a)
        ff(b=b)
        ff(c)
        ff(args)
        ff(my_kwargs=kwargs)

    ff.config(simple=True)

    multi(5, 2)
    ff(foo)(1, b=2, c=4, unseen1=None, unseen2='abc')
    foo(1, 2, 3, 4, 5, 6, unseen3=7, unseen4=8)

    ff()

def example3():
    @ff
    def foo(a, b=2, *args, **kwargs):
        ff('{} + {} = {}',a,b,a+b)
        return a+b

    foo(1, b=3, unseen1=None, unseen2='abc')
    ff()


if __name__ == '__main__':
    example3()


