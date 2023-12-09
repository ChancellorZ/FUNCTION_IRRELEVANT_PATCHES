import networkx,cpgqls_client,json,subprocess,conf,clang
class dfs_seq_node:
	def __init__(self,id=0,at=0,fa=0):
		self.id=id
		self.right_bound=0
		self.attr=at
		self.father=fa
	def __getitem__(self, i):
		if self.attr.__contains__(i):return self.attr[i]
		else: return None
	def __setitem__(self,i,v):
		if self.attr.__contains__(i):
			self.attr[i]=v
			return v
		else: return None
class function_info:
	def __init__(self,n=None,s=0,e=0):
		self.name=n
		self.start=s
		self.end=e
		self.argv=set()
class ctl_statement:
	def __init__(self,cp=0,t='',lp=0):
		self.condition_param=cp
		self.stmt_type=t
		self.loop_param=lp
		self.son=[]
param_regs={
	#arch:[(param_reg),reg_pos,stack_reg]
	'AMD64':[('rdi','rsi','rdx','rcx','r8','r9'),'base','rbp'],
	'AARCH64':[('x0','x1','x2','x3','x4','x5','x6','x7'),'top','xsp'],
}
ctl_statement_attribute={
"ForStatement":ctl_statement(2,'loop',4),
	#for(i=0;i<3;i++)xxx
	#1 i=0
	#2 i<3
	#3 i++
	#4 xxx
"WhileStatement":ctl_statement(1,'loop',2),
	#while(i<0)i++;
	#1 i<0
	#2 i++
"IfStatement":ctl_statement(1,'branch'),
	#if(i<0)i++;else i--;
	#1 i<0
	#2 i++
	#3 else i--
"ElseStatement":ctl_statement(None,'branch')
#TODO other control statements do while do until switch case...
}
class change_info:
	def __init__(self,fa,fb):
		self.fa=fa
		self.fb=fb
		self.get_data()
		self.get_line_map()
		self.a_tree=clang.cindex.Index.create().parse(fa).cursor
		self.b_tree=clang.cindex.Index.create().parse(fb).cursor
		self.intresting_data={}
		self.add_intresting_function(self.a_tree,self.fa,self.change_range[0])
		self.add_intresting_function(self.b_tree,self.fb,self.change_range[1])
		# self.filter_good_function()
		# print("intresting function get")
		# self.acpg_list=self.query_cpg(fa)
		# print("a cpg get")
		# self.bcpg_list=self.query_cpg(fb)
		# print("b cpg get")
	def solve(self):
		res={}
		for tp in self.intresting_data:
			res[tp]={'add':[],'change':[],'del':[]}
			for name in self.intresting_data[tp]:
				ina=inb=False
				for cursor in self.a_tree.get_children():
					if tp==cursor.kind.name and name==cursor.spelling:
						ina=True
						break
				for cursor in self.b_tree.get_children():
					if tp==cursor.kind.name and name==cursor.spelling:
						inb=True
						break
				if ina and inb:res[tp]['change'].append(name)
				elif not ina:res[tp]['add'].append(name)
				else:res[tp]['del'].append(name)
		num=0
		for cr in self.change_range[0]:num+=cr[1]-cr[0]
		for cr in self.change_range[1]: num+=cr[1]-cr[0]
		return {'change kind':res,'change lines':num}
	def filter_good_function(self):
		res=[]
		for fn,use in self.intresting_function.items():
			ok1=False
			for x in self.a_function_list:
				if fn==x['name']:ok1=True
			ok2=False
			for x in self.a_function_list:
				if fn == x['name']: ok2 = True
			if ok1 and ok2:res.append((fn,use))
		self.intresting_function=res
	def get_data(self):
		with open(self.fa, "r") as f:self.adata=f.read().split('\n')
		with open(self.fb, "r") as f:self.bdata=f.read().split('\n')
	def get_line_map(self):
		self.a2b = [None for x in range(len(self.adata)+1)]
		self.b2a = [None for x in range(len(self.bdata)+1)]
		self.change_range = [[], [], []]
		file_diff = subprocess.run(["diff", self.fa, self.fb], capture_output=True, encoding='utf-8').stdout.split('\n')
		al = bl = 0
		def fill(a, b):
			nonlocal al, bl
			while al < a and bl < b:
				self.a2b[al] = bl
				self.b2a[bl] = al
				al = al + 1
				bl = bl + 1
		for line in file_diff:
			if len(line) == 0 or "0123456789".find(line[0]) == -1: continue
			ch = 'a' if 'a' in line else ('d' if 'd' in line else 'c')
			l = line[0:line.find(ch)]
			r = line[line.find(ch) + 1:]

			def get_range(x):
				if ',' in x:
					return [int(x[:x.find(',')]), int(x[x.find(',') + 1:])]
				else:
					return [int(x), int(x)]
			l = get_range(l)
			r = get_range(r)
			fill(l[0], r[0])
			if ch == 'a':
				r[1] = r[1] + 1
			elif ch == 'd':
				l[1] = l[1] + 1
			else:
				l[1] = l[1] + 1
				r[1] = r[1] + 1
			al = l[1]
			bl = r[1]
			self.change_range[0].append(l)
			self.change_range[1].append(r)
			self.change_range[2].append(ch)
		fill(len(self.adata)+1, len(self.bdata)+1)
	def add_intresting_function(self,root,file,cr):
		for cursor in root.get_children():
			if cursor.extent.start.file==None:continue
			csfile=cursor.extent.start.file.name
			if cursor.extent.end.file==None:continue
			cefile=cursor.extent.end.file.name
			if csfile!=file or cefile!=file:continue
			tp=cursor.kind.name
			start=cursor.extent.start.line
			end=cursor.extent.end.line
			name=cursor.spelling
			for c in cr:
				if c[0]<=end and c[1]>start:
					self.intresting_data.setdefault(tp,set())
					self.intresting_data[tp].add(name)
	def query_cpg(self,f):
		cpgs=[]
		query_code = """val source = scala.io.Source.fromFile(\"%s\")
		importCode.c.fromString(try source.mkString finally source.close())"""%f
		self.Q(query_code)
		for fname,pos in self.intresting_function:
			query_code="""val ast=cpg.method.filter(_.isExternal==false).name(\"%s\").ast
val writer = new java.io.PrintWriter(file)
writer.write(ast.toJson)
writer.close()"""%fname
			self.Q(query_code)
			with open(self.tmp_file, 'r') as load_f: node_info = json.load(load_f)
			query_code = """val graph=cpg.method.name(\"%s\").dotCpg14
val writer = new java.io.PrintWriter(file)
writer.write(graph.l.head)
writer.close()""" % fname
			self.Q(query_code)
			with open(self.tmp_file,"r")as dot :dotfile=dot.read()
			dotfile=dotfile.split('\n')
			cpg=networkx.MultiDiGraph()
			cpg.graph['name']=dotfile[0].split(' ')[1]
			for l in dotfile:
				if l.startswith(' '):
					t=l.split(' ',5)
					u=int(t[2][1:-1])
					v=int(t[4][1:-1])
					attr=t[5]
					attr=attr[attr.find('\"')+1:attr.rfind('\"')]
					cpg.add_edge(u,v,label=attr)
			for nid in cpg.nodes:
				for node in node_info:
					if node.__contains__('id') and node['id'] == nid:
						cpg.nodes[nid].update(node)
						if node['_label'] == 'METHOD':cpg.graph['method node']=nid
			cpgs.append(cpg)
		return cpgs

# diff --git a/ssl/ssl_sess.c b/ssl/ssl_sess.c
# index fd94054..c639e53 100644
# --- a/ssl/ssl_sess.c
# +++ b/ssl/ssl_sess.c
# @@ -239,39 +239,57 @@ SSL_SESSION *ssl_session_dup(SSL_SESSION *src, int ticket)
#      }
#      memcpy(dest, src, sizeof(*dest));
# +    if (src->sess_cert != NULL)
# +        CRYPTO_add(&src->sess_cert->references, 1, CRYPTO_LOCK_SSL_SESS_CERT);
# +