from __future__ import annotations
from dataclasses import dataclass

class Data:
    pass

class Directory:
    def create_file(self, name: str) -> File: ...

class File:
    def append_data(self, data: t.Union[str, Data]) -> None: ...

def create_file_with_contents(dir: Directory, name: str, arg: Data) -> File:
    file = dir.create_file(name)
    file.append_data(arg)
    return file

def another(dir: Directory, arg1: Data, arg2: Data) -> File:
    paths = dir.create_file("paths")
    arg1_file = create_file_with_contents(dir, "arg1", arg1)
    paths.append_data("arg1 file path:")
    paths.append_data(arg1_file)
    arg2_file = create_file_with_contents(dir, "arg2", arg2)
    paths.append_data("arg2 file path:")
    paths.append_data(arg2_file)
    return paths


##### IO
# TODO


##### Testing
@dataclass
class TestDirectory(Directory):
    def create_file(self, name: str) -> File:
        return TestFile(open(self.path/name, 'r'))

@dataclass
class TestFile(File):
    def append_data(self, data: t.Union[str, Data, File]) -> None:
        read_data = self.file.read(len(data))
        assert_equal(read_data, data)

def testmain():
    dir = IODirectory([], "mydir")
    arg1 = Data("somearg")
    arg2 = Data("otherarg")
    dir = IODirectory.make_tempdir()
    result = another(dir, arg1, arg2)
    # test that the files contain the expected content
    another(TestDirectory(dir.name), arg1, arg2)


##### Pretty printing
@dataclass
class PPDirectory(Directory):
    program: t.List[str]
    variable_name: str

    def create_file(self, name: str) -> File:
        file = PPFile(self.program, f"file{len(self.program)}")
        self.program.append(f"{file.variable_name} = {self.variable_name}.create_file('{name}')")
        return file

@dataclass
class PPFile(File):
    program: t.List[str]
    variable_name: str

    def append_data(self, data: t.Union[str, Data, File]) -> None:
        if isinstance(data, str):
            self.program.append(f"{self.variable_name}.append_data('{data}')")
        else:
            assert isinstance(data, PPData) or isinstance(data, PPFile)
            self.program.append(f"{self.variable_name}.append_data({data.variable_name})")

@dataclass
class PPData(Data):
    variable_name: str

def ppmain():
    dir = PPDirectory([], "mydir")
    arg1 = PPData("somearg")
    arg2 = PPData("otherarg")
    result = another(dir, arg1, arg2)
    print(f"def func({dir.variable_name}, {arg1.variable_name}, {arg2.variable_name}):")
    print("    " + "\n    ".join(result.program))

ppmain()


##### Optimiziation

@dataclass
class OptimizingDirectory(Directory):
    def create_file(self, name: str) -> File:
        file = OptimizingFile()
        self.files[name] = file
        return file

@dataclass
class OptimizingFile(File):
    def append_data(self, data: t.Union[str, Data, File]) -> None:
        self.size += len(data)

@dataclass
class OptimizedDirectory(IODirectory):
    def preallocate_files(self) -> None:
        for name, size in files.items():
            self.files = super().create_file(name, size=size)

    def create_file(self, name: str) -> IOFile:
        return self.files[name]

def testmain():
    arg1 = Data("somearg")
    arg2 = Data("otherarg")
    optdir = OptimizingDirectory()
    another(optdir, arg1, arg2)
    dir = OptimizedDirectory("somedir")
    dir.preallocate_files(optdir.files)
    another(dir, arg1, arg2)
    
