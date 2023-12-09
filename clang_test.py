import clang.cindex
from clang.cindex import Index  # 主要API
from clang.cindex import Config  # 配置
from clang.cindex import TranslationUnit
from clang.cindex import CursorKind  # 索引结点的类别
from clang.cindex import TypeKind  # 节点的语义类别

# 这个路径需要自己先在笔记本上安装
if Config.loaded==True:
	print("Config.loaded == True:")
	# pass
else:
	libclangPath='/usr/lib/llvm-10/lib/libclang.so'
	Config.set_library_file(libclangPath)
	print("install path")


def preorder_travers_AST(cursor):
	children=list(cursor.get_children())
	print(cursor.spelling,end='\t')
	print(len(children),end='\t')
	print(cursor.extent.start.line,cursor.extent.end.line,end='\t')
	print(cursor.kind.name)
	# for cur in cursor.get_children():
	# 	preorder_travers_AST(cur)


if __name__=='__main__':
	file_path="test.c"
	index=Index.create()

	tu=index.parse(file_path)
	AST_root_node=tu.cursor  # cursor根节点
	print(AST_root_node)
	for cursor in AST_root_node.get_children():
		preorder_travers_AST(cursor)
