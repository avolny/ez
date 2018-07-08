# ez
toolset of simple python tools that make config files and



# fastprint

```
from ez.ezprint import ff
```

fastprint is a set of tools set to make `print`ing a pleasant experience. `ff` is the main and only object used. the letter `f` is the first key on the left home row. programmers use the right hand a lot, `f` is therefore the key that costs the least amount of energy and focus to press (including the fact that the index finger is the strongest).

`ff` maintains a json dictionary that contains contents of all desired prints outs.

It can also automatically print tree of function calls and include prints of arguments and return values of each function (and methods of each class) that is decorated by `@ff`. `ff` prints only decorated functions therefore

printing can be done manually `ff('abcd')`, values can be named `ff(text='ghij')`, `ff` can be used as a complete shortcut for string .format, as ff('{} + {} = {}',3,5,3+5) is equivalent to ff('{} + {} = {}'.format(3,5,3+5))

use `ff()` to print out the contents

use `str(ff)` to get just the string

```
from ez.ezprint import ff
ff('abcd')
ff(text='ghij')
ff('{} + {} = {}',3,5,3+5)
ff()
```

prints

```
{
print: {
  str_0: abcd,
  text_1: ghij,
  str_2: 3 + 5 = 8
  },
calls: {}
}
```

when writing and debugging code, one often finds the need to print function parameters, return values and intermediate values. when many functions are called, the prints get messy and the hierarchical order is not quite clear. one starts adding landmarks or checkpoints which signify start or end of some function to orient in the mess.

`ff` can be used as a decorator for both functions and classes (and their methods), simply as `@ff`, this automatically tracks all calls of decorated function (or method from decorated class) and prints argument names with values of the call, return values and all the prints that happened during the call are included in dictionary that contains the sub-tree of the call hierarchy.

This works in addition to all introduced concepts, while all the prints that happen during a call are included in the hierarchical structure. you can clearly see what was printed in what sub-call of what sub-tree of all the calls, you have to do very little for it. just include `@ff` before your function or class.

when working on something bigger, decorating all functions or classes would blow up your print output so it becomes desirable to inspect and print just the functions you are interested in. for that use `ff` to decorate function just for a single call. `ff(myfunc)(arg1,arg2,arg3)` is equivalent to defining `myfunc` with the `@ff` decorator and calling it. also, `@ff` maintains structure if you use it only for some methods in the call tree.

for simple print use `ff.config(simple=True)`

```
from ez.ezprint import ff

@ff
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
```

prints

```
{
print: {},
calls: {
  000_multi: {
    001_add: {
      002_str: 0 + 5 = 5
      },
    003_add: {
      004_str: 5 + 5 = 10
      },
    005_str: 5 * 2 = 10
    },
  006_foo: {
    007_int: 1,
    008_b: 2,
    009_int: 4,
    010_tuple: (),
    011_my_kwargs: {'unseen1': None, 'unseen2': 'abc'}
    },
  012_int: 1,
  013_b: 2,
  014_int: 3,
  015_tuple: (4, 5, 6),
  016_my_kwargs: {'unseen3': 7, 'unseen4': 8}
  }
}
```

to display all the values, don't set the `simple` flag to true (it's false by default).


```
from ez.ezprint import ff

@ff
def foo(a, b=2, *args, **kwargs):
    ff('{} + {} = {}',a,b,a+b)
    return a+b

foo(1, b=3, unseen1=None, unseen2='abc')
ff()
```

prints

```
{
print: {},
calls: {
  000_foo: {
    args: {
      a: 1,
      b: 3,
      args: [],
      kwargs: {
        unseen1: None,
        unseen2: abc
        }
      },
    calls: {
      001_str: 1 + 3 = 4
      },
    retval: [4]
    }
  }
}
```

# ezconfig

documentation incoming. see code and use in `ezprint` to understand, it's quite easy and the `ezconfig` code is quite well documented