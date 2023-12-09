#include<bits/stdc++.h>
using namespace std;
int vis[1<<21];
int cnt[1<<21];
void solve(int l,int r,int sz){
	if(l+1==r){
		vis[l]=cnt[l];
		return;
	}
	int mid=(l+r)>>1;
	solve(l,mid,sz>>1);
	solve(mid,r,sz>>1);
	for(int i=l;i<mid;i++)
		vis[i]+=vis[i+sz];
}
int main()
{
	freopen("xxx.txt","r",stdin);
	freopen("z.txt","w",stdout);
	memset(vis,0,sizeof(vis));
	memset(cnt,0,sizeof(cnt));
	for(int i=0;i<(1<<21);i++)
		scanf("%d\n",cnt+i);
	solve(0,1<<21,1<<20);
	for(int i=0;i<(1<<21);i++){
		printf("%d\n",vis[i]);
	}
	return 0;
}