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
    def create_file(self, name: str) -> File:
        "Create and return a file in this directory"
        ...

class File:
    "A file, to which we can append several kinds of data"
    def append_data(self, data: t.Union[str, Data, File]) -> None:
        """Append this piece of data to the file

        When passed another file, we append the path of that file to
        this file.

        """
        ...

def create_file_with_contents(dir: Directory, name: str, arg: Data) -> File:
    "A helper function to create a file containing some data"
    file = dir.create_file(name)
    file.append_data(arg)
    return file

def prog(dir: Directory, arg1: Data, arg2: Data) -> File:
    "A simple program manipulating files and directories"
    paths = dir.create_file("paths")
    arg1_file = create_file_with_contents(dir, "arg1", arg1)
    paths.append_data("arg1 file path:")
    paths.append_data(arg1_file)
    arg2_file = create_file_with_contents(dir, "arg2", arg2)
    paths.append_data("arg2 file path:")
    paths.append_data(arg2_file)
    return paths


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
        f = open(path, 'w')
        if size:
            f.truncate(size)
        return IOFile(path, f)

@dataclass
class IOFile(File):
    "A file in the filesystem, to which we'll write"
    path: str
    file: t.TextIO

    def append_data(self, data: t.Union[str, StrData, IOFile]) -> None:
        """Convert data to a string and append it to this file

        As we write data to the file, the file position moves forward
        and the file grows.

        """
        if isinstance(data, str):
            self.file.write(data)
        elif isinstance(data, StrData):
            self.file.write(data.content)
        else:
            assert isinstance(data, IOFile)
            self.file.write(data.path)


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

@dataclass
class TestFile(File):
    "A file in the filesystem, which we'll read from"
    path: str
    file: t.TextIO

    def append_data(self, data: t.Union[str, Data, TestFile]) -> None:
        """Convert data to a string and assert it matches the file

        As we read data from the file, the file position moves forward
        and we read new data.

        """
        if isinstance(data, str):
            expected = data
        elif isinstance(data, StrData):
            expected = data.content
        else:
            assert isinstance(data, TestFile)
            expected = data.path
        read_data = self.file.read(len(expected))
        if expected != read_data:
            raise Exception("the next data in the file should be", expected, "not", read_data)

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
@dataclass
class PPDirectory(Directory):
    "A staged directory, which writes lines of code to perform requested operations"
    program: t.List[str]
    variable_name: str

    def create_file(self, name: str) -> PPFile:
        "Write a line of code to create a file and store it in an arbitrarily named variable"
        file = PPFile(self.program, f"file{len(self.program)}")
        self.program.append(f"{file.variable_name} = {self.variable_name}.create_file('{name}')")
        return file

@dataclass
class PPFile(File):
    "A staged file, which writes lines of code to perform requested operations"
    program: t.List[str]
    variable_name: str

    def append_data(self, data: t.Union[str, PPData, PPFile]) -> None:
        "Convert data to a variable name or string literal, and write a line of code to append it to this file"
        if isinstance(data, str):
            self.program.append(f"{self.variable_name}.append_data('{data}')")
        else:
            assert isinstance(data, PPData) or isinstance(data, PPFile)
            self.program.append(f"{self.variable_name}.append_data({data.variable_name})")

@dataclass
class PPData(Data):
    "A staged piece of data, which exists only as a variable name"
    variable_name: str

def ppmain():
    dir = PPDirectory([], "mydir")
    arg1 = PPData("somearg")
    arg2 = PPData("otherarg")
    prog(dir, arg1, arg2)
    print(f"def func({dir.variable_name}, {arg1.variable_name}, {arg2.variable_name}):")
    print("    " + "\n    ".join(dir.program))

# ppmain()


##### Optimization
# This implementation optimizes the program it's passed to, storing information
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

    def optimized(self) -> OptimizedDirectory:
        "Return an optimized directory which performs profiled space allocations all at once"
        return OptimizedDirectory(self.path, self.files)

@dataclass
class ProfilingFile(File):
    "A staged file, which profiles the space usage of the program"
    path: str
    size: int = 0

    def append_data(self, data: t.Union[str, StrData, ProfilingFile]) -> None:
        "Convert data to a string and record how much file space writing it would consume"
        if isinstance(data, str):
            self.size += len(data)
        elif isinstance(data, StrData):
            self.size += len(data.content)
        else:
            assert isinstance(data, ProfilingFile)
            self.size += len(data.path)

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
