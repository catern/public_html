"""Examples for "Write code, not compilers"

Read http://catern.com/tfs.html first.

Then come here for an example of how you actually do that.

"""
from __future__ import annotations
from dataclasses import dataclass
import typing as t


##### Program
class Data:
    "Some opaque piece of data"
    pass

class Directory:
    "A directory, in which we can create files"
    def create_file(self, name: str) -> File: ...
    def for_each_file(self, f: t.Callable[[File], None]) -> None: ...

class File:
    "A file, to which we can append several types of values"
    def append_str (self, data: str ) -> None: ...
    def append_data(self, data: Data) -> None: ...
    def append_path(self, data: File) -> None: ...
    def close(self) -> None: ...

def create_file_with_contents(dir: Directory, name: str, arg: Data) -> File:
    "A helper function to create a file containing some data"
    file = dir.create_file(name)
    file.append_data(arg)
    return file

def prog(dir: Directory, arg1: Data, arg2: Data) -> None:
    """A simple program manipulating files and directories

    We will be reinterpreting this program in different ways by passing it
    different arguments, which are different implementations of Directory and
    Data.

    """
    paths = dir.create_file("paths")
    arg1_file = create_file_with_contents(dir, "arg1", arg1)
    paths.append_str("arg1 file path:")
    paths.append_path(arg1_file)
    arg1_file.close()
    arg2_file = create_file_with_contents(dir, "arg2", arg2)
    paths.append_str("arg2 file path:")
    paths.append_path(arg2_file)
    arg2_file.close()
    paths.append_str("all paths:")
    def f(file: File) -> None:
        paths.append_path(file)
        file.close()
    dir.for_each_file(f)
    paths.close()


##### IO
# This implementation of Data/Directory/File does the obvious thing:
# It writes to the filesystem.
@dataclass
class StrData(Data):
    "Some data, specifically a string"
    content: str

    def serialize(self) -> str:
        return self.content

@dataclass
class IODirectory(Directory):
    "A directory in the filesystem, in which we'll create files"
    path: str

    def create_file(self, name: str, size: int=None) -> IOFile:
        """Open and create a file in this directory in the filesystem

        We have an optional argument, size, to preallocate space in
        the file for future writes.

        """
        path = self.path + "/" + name
        file = open(path, 'w')
        if size:
            file.truncate(size)
        return IOFile(path, file)

    def for_each_file(self, f: t.Callable[[File], None]) -> None:
        "Call `f` with each file in this directory"
        for name in os.listdir(self.path):
            path = self.path + "/" + name
            f(IOFile(path, open(path, 'r')))

@dataclass
class IOFile(File):
    "A file in the filesystem, to which we'll write"
    path: str
    file: t.TextIO

    def append_str(self, data: str) -> None:
        "Append this string to this file"
        self.file.write(data)

    def append_data(self, data: StrData) -> None:
        self.file.write(data.content)

    def append_path(self, data: IOFile) -> None:
        self.file.write(data.path)

    def close(self) -> None:
        self.file.close()


##### Testing
# This implementation inverts the expected sense of Data/Directory/File.
# - Instead of creating a file, we assert that the file is there.
# - Instead of writing to the file, we assert that the contents of the
#   file match our expectation.
@dataclass
class TestDirectory(Directory):
    "A directory in the filesystem, in which we'll open files"
    path: str

    def create_file(self, name: str) -> TestFile:
        """Open a file in this directory in the filesystem

        If the file doesn't exist, we'll throw an exception.

        """
        path = self.path + "/" + name
        # throws on non-existent file
        f = open(path, 'r')
        return TestFile(path, f)

    def for_each_file(self, f: t.Callable[[File], None]) -> None:
        """Call `f` with each file in this directory.

        Same as for IODirectory.
        """
        for name in os.listdir(self.path):
            path = self.path + "/" + name
            f(TestFile(path, open(path, 'r')))

@dataclass
class TestFile(File):
    "A file in the filesystem, which we'll read from"
    path: str
    file: t.TextIO

    def append_str(self, data: str) -> None:
        """Assert this string matches the data in this file

        As we read data from the file, the file position moves forward
        and we read new data.

        """
        read_data = self.file.read(len(data))
        if data != read_data:
            raise Exception("the next data in the file should be", data, "not", read_data)

    def append_data(self, data: StrData) -> None:
        self.append_str(data.content)

    def append_path(self, data: TestFile) -> None:
        self.append_str(data.path)

    def close(self) -> None:
        self.file.close()

def testmain():
    """Test IODirectory by running TestDirectory.

    First, we run `prog` with IODirectory.  Then, we run `prog` with
    TestDirectory to make sure that IODirectory worked right.

    """
    dir = IODirectory("/tmp/somedir")
    arg1 = StrData("my very cool and neat data")
    arg2 = StrData("some other kind of cool and neat data")
    prog(dir, arg1, arg2)
    prog(TestDirectory(dir.path), arg1, arg2)

# testmain()


##### Pretty printing
# This implementation of Data/Directory/File pretty-prints the program
# it's passed to.
import contextlib
import textwrap

@dataclass
class Program:
    statements: t.List[str]
    name: str

    def var(self, name: str) -> str:
        "Generate a fresh, unused variable name from this name"
        return self.name + "_" + name + str(len(self.statements))

    @contextlib.contextmanager
    def def_function(self, name: str, args: t.List[str]) -> str:
        """Helper for pretty-printing function definitions

        Statements performed inside this context manager are part of the
        function definition.

        """
        parent_statements, parent_name = self.statements, self.name
        self.statements, self.name = [], self.var(name)
        yield self.name
        parent_statements.append(
            f"def {self.name}(" + ", ".join(args) + "):\n" +
            textwrap.indent("\n".join(self.statements), "    "))
        self.statements, self.name = parent_statements, parent_name

@dataclass
class PPDirectory(Directory):
    "A staged directory, which writes lines of code to perform requested operations"
    program: Program
    variable_name: str

    def create_file(self, name: str) -> PPFile:
        "Write a line of code to call .create_file and store the result in an arbitrarily named variable"
        file = PPFile(self.program, self.program.var("file"))
        self.program.statements.append(f"{file.variable_name} = {self.variable_name}.create_file('{name}')")
        return file

    def for_each_file(self, f: t.Callable[[File], None]) -> None:
        "Render the passed function as a function definition, then write a line of code to call .for_each_file with it."
        file = PPFile(self.program, self.program.var("file"))
        with self.program.def_function('f', [file.variable_name]) as func_name:
            f(file)
        self.program.statements.append(f"{self.variable_name}.for_each_file({func_name})")

@dataclass
class PPFile(File):
    "A staged file, which writes lines of code to perform requested operations"
    program: Program
    variable_name: str

    def append_str(self, data: str) -> None:
        "Write a line of code to call .append_str with this string constant"
        self.program.statements.append(f"{self.variable_name}.append_str('{data}')")

    def append_data(self, data: PPData) -> None:
        "Convert data to a variable name, and write a line of code to call .append_str with it"
        self.program.statements.append(f"{self.variable_name}.append_data({data.variable_name})")

    def append_path(self, data: PPFile) -> None:
        "Convert data to a variable name, and write a line of code to call .append_path with it"
        self.program.statements.append(f"{self.variable_name}.append_path({data.variable_name})")

    def close(self) -> None:
        "Write a line of code to call .close"
        self.program.statements.append(f"{self.variable_name}.close()")

@dataclass
class PPData(Data):
    "A staged piece of data, which exists only as a variable name"
    variable_name: str

def ppmain():
    program = Program([], "")
    dir = PPDirectory(program, "mydir")
    arg1 = PPData("somearg")
    arg2 = PPData("otherarg")
    with program.def_function('main', [dir.variable_name, arg1.variable_name, arg2.variable_name]):
        prog(dir, arg1, arg2)
    print(program.statements[0])

# ppmain()
# Output:
# def func(mydir, somearg, otherarg):
#     file0 = mydir.create_file('paths')
#     file1 = mydir.create_file('arg1')
#     file1.append_data(somearg)
#     file0.append_data('arg1 file path:')
#     file0.append_data(file1)
#     file5 = mydir.create_file('arg2')
#     file5.append_data(otherarg)
#     file0.append_data('arg2 file path:')
#     file0.append_data(file5)


##### Optimization
# This implementation profiles the program it's passed to, storing information
# about the file space allocation performed by the program and returning a new
# Directory which batches those allocations together and performs them all at
# once.
# (Background knowledge: Allocating filesystem space in many small chunks is
# substantially less efficient than allocating it all at once in one big
# request)
@dataclass
class ProfilingDirectory(Directory):
    "A staged directory, which returns files which profile the space usage of the program"
    path: str
    files: t.Dict[str, ProfilingFile]

    def create_file(self, name: str) -> File:
        "Make a file which profiles the space usage of operations performed on it"
        path = self.path + "/" + name
        file = ProfilingFile(path)
        self.files[name] = file
        return file

    def for_each_file(self, f: t.Callable[[File], None]) -> None:
        "Does nothing; this depends on data in the filesystem, so we can't statically profile this"
        pass

    def optimized(self) -> OptimizedDirectory:
        "Return an optimized directory which performs profiled space allocations all at once"
        return OptimizedDirectory(self.path, self.files)

@dataclass
class ProfilingFile(File):
    "A staged file, which profiles the space usage of the program"
    path: str
    size: int = 0

    def append_str(self, data: str) -> None:
        "Record how much file space writing this string would consume"
        self.size += len(data)

    def append_data(self, data: StrData) -> None:
        "Record how much file space writing this data would consume"
        self.append_str(data.content)

    def append_path(self, data: ProfilingFile) -> None:
        "Record how much file space writing this path would consume"
        self.append_str(data.path)

    def close(self) -> None:
        pass

@dataclass
class OptimizedDirectory(IODirectory):
    """An optimized directory, which will allocate space all at once instead of in small chunks

    Background knowledge: Allocating filesystem space in many small chunks is
    substantially less efficient than allocating it all at once in one big
    request.
    """
    profiler_results: t.Dict[str, ProfilingFile]

    def create_file(self, name: str) -> IOFile:
        profiler_result = self.profiler_results.get(name)
        if profiler_result:
            return super().create_file(name, size=profiler_result.size)
        else:
            return super().create_file(name)

def optimized_main():
    arg1 = StrData("somearg")
    arg2 = StrData("otherarg")
    optdir = OptimizingDirectory("somedir", {})
    prog(optdir, arg1, arg2)
    dir = optdir.optimized()
    prog(dir, arg1, arg2)

# optimized_main()

##### Linear types
@dataclass
class TypecheckingDirectory(Directory):
    def create_file(self, name: str) -> TypecheckingFile:
        "Make a file which profiles the space usage of operations performed on it"
        return TypecheckingFile(open=True)

    def for_each_file(self, f: t.Callable[[File], None]) -> None:
        # run f to type check it against the input typestate...
        try:
            f(TypecheckingFile(open=True))
        except AssertionError:
            e.args = ("function passed to for_each_file uses closed file on the first run",)
            raise
        # ...and then run f again to check it against its own output typestate.
        try:
            f(TypecheckingFile(open=True))
        except AssertionError as e:
            e.args = ("function passed to for_each_file uses closed files on second and future runs",)
            raise

@dataclass
class TypecheckingFile(File):
    open: bool

    def append_str(self, data: str) -> None:
        assert self.open

    def append_data(self, data: Data) -> None:
        assert self.open

    def append_path(self, data: File) -> None:
        assert self.open

    def close(self) -> None:
        assert self.open
        self.open = False

def badprog(dir: Directory) -> File:
    paths = dir.create_file("paths")
    def f(file: File) -> None:
        paths.append_path(file)
        # oops, we meant to close "file", not "paths"!
        paths.close()
    dir.for_each_file(f)
    return paths

def typechecking_main():
    prog(TypecheckingDirectory(), Data(), Data())
    badprog(TypecheckingDirectory())

typechecking_main()

##### Type-correct interfaces
# The type declarations for the Data/File/Directory interfaces at the start are
# simple and correct, but need to be made a little more generic to support our
# implementations; otherwise we get some type errors. The below declarations of
# the interfaces are correct and allows us to typecheck just fine.

class Data:
    pass

TData = t.TypeVar('TData', bound=Data)
TFile = t.TypeVar('TFile', bound=File)
class File(t.Generic[TData]):
    def append_data(self: TFile, data: t.Union[str, TData, TFile]) -> None: ...

class Directory(t.Generic[TFile]):
    def create_file(self, name: str) -> TFile: ...
