/*
Maximilien Danisch
Septembre 2017
http://bit.ly/danisch
maximilien.danisch@gmail.com

to compile:
gcc PageRank.c -o PageRank -O9

to execute:
./PageRank citnet.csv pagerank.csv
net.txt should contain on each line: "i,j\n" that is the input directed graph.
pagerank.txt contains an approximation of the pagerank (20 iterations using the power iteration method) with a restart probability of 0.15. "nodeID PageRankValue\n" on each line.
*/

#include <stdlib.h>
#include <stdio.h>
#include <math.h>
#include <strings.h>

#define NLINKS 4678025 //maximum number of nonzero entries, will increase if needed
#define NITER 300 //Number of power iterations to compute pagerank
#define ALPHA 0.15 //restart probability of pagerank

// graph datastructure:
typedef struct {
	unsigned long s;//source node
	unsigned long t;//target node
} edge;

//sparse graphe structure
typedef struct {
	unsigned long n;//number of nodes
	unsigned long e;//number of edges
	edge *el;//edge list
	unsigned long *dout;//outdegree
} sparse;

//compute the maximum of three unsigned long
inline unsigned long max3(unsigned long a,unsigned long b,unsigned long c){
	a=(a>b) ? a : b;
	return (a>c) ? a : c;
}

//reading the weighted sparsematrix
sparse* readedgelist(char* edgelist){
	unsigned long i, e1=NLINKS;
	sparse *g=malloc(sizeof(sparse));
	g->el=malloc(e1*sizeof(edge));
	FILE *file;
	g->n=0;
	g->e=0;
	file=fopen(edgelist,"r");
	while (fscanf(file,"%lu,%lu\n", &(g->el[g->e].s), &(g->el[g->e].t))==2) {
		g->n=max3(g->n,g->el[g->e].s,g->el[g->e].t);
		if (g->e++==e1) {
			e1+=NLINKS;
			g->el=realloc(g->el,e1*sizeof(edge));
		}
	}
	fclose(file);
	g->n++;
	g->el=realloc(g->el,g->e*sizeof(edge));

	//computing out-degrees
	g->dout=calloc(g->n,sizeof(unsigned long));
	for (i=0;i<g->e;i++){
		g->dout[g->el[i].s]++;
	}

	return g;
}

//free the graph stucture
void freegraph(sparse *g){
	free(g->el);
	free(g->dout);
	free(g);
}

//one step of random walk on the graph: initial probalities in v1 and result stored in v2
void onestep(sparse* g, double* v1, double* v2){
	unsigned long i;
	bzero(v2,sizeof(double)*g->n);
	//for (i=0;i<g->n;i++){//divide by dout here or for each edge
	//	v1[i]/=((double)(g->dout[i]));
	//}
	for (i=0;i<g->e;i++){
		v2[g->el[i].t]+=v1[g->el[i].s]/((double)(g->dout[g->el[i].s]));//
	}
}

//returns an approximation of the pagerank (restar probability=a, number of iterations=k)
double* pagerank(sparse* g, double a, unsigned char k){
	double *v1,*v2,*v3;
	double s;
	unsigned char i;
	unsigned long j,n=g->n;

	v1=malloc(n*sizeof(double));

	for (j=0;j<n;j++){//initialisation
		v1[j]=1./((double)n);
	}
	v2=malloc(n*sizeof(double));

	for (i=0;i<k;i++){
		onestep(g,v1,v2);//one step of random walk stored in v2
		s=0;//to normalize
		for (j=0;j<g->n;j++){
			v2[j]=v2[j]*(1.-a)+a/((double)n);
			s+=v2[j];
		}
		s=(1-s)/((double)n);
		for (j=0;j<n;j++){
			v2[j]+=s;
		}
		v3=v2,v2=v1,v1=v3;
	}

	free(v2);
	return v1;
}

void printres(FILE* file,unsigned long n, double* vect){
	unsigned long i;
	for (i=0;i<n;i++){
		fprintf(file,"%lu,%1.12f\n",i,vect[i]);
	}
}

int main(int argc,char** argv){
	sparse* g;
	double* pr;
	FILE* file=fopen(argv[2],"w");

	size_t t1,t2;

	t1=time(NULL);

	printf("Reading edgelist from file %s\n",argv[1]);

	g=readedgelist(argv[1]);

	printf("Number of nodes = %lu\n",g->n);
	printf("Number of edges = %lu\n",g->e);

	printf("Computing approximation of pagerank\n");

	pr=pagerank(g,ALPHA,NITER);

	printres(file,g->n,pr);
	fclose(file);

	//prints the outdegrees in text file named outdegrees.txt
	file=fopen("outdegrees.txt","w");
	unsigned long i;
	for (i=0;i<g->n;i++){
		fprintf(file,"%lu,%lu\n",i,g->dout[i]);
	}
	fclose(file);

	//prints the indegrees in text file named indegrees.txt
	unsigned long *din=calloc(g->n,sizeof(unsigned long));
	unsigned long j;
	for (j=0;j<g->e;j++){
		din[g->el[j].t]++;
	}
	file=fopen("indegrees.txt","w");
	for (j=0;j<g->n;j++){
		fprintf(file,"%lu,%lu\n",j,din[j]);
	}
	fclose(file);
	free(din);


	freegraph(g);

	t2=time(NULL);

	printf("Overall time = %ldh%ldm%lds\n",(t2-t1)/3600,((t2-t1)%3600)/60,((t2-t1)%60));

	return 0;
}

