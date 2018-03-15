import networkx as nx
import numpy as np
import scipy 

class Sim(object):
    def __init__(self, rate, size, res_factor,
                 graph=False, Nmonte_points=10000,error=False):
        self.rate = rate 
        self.size = size
        self.area = size * size 
        self.res_factor = res_factor # for final coverage estimation
        self.graph = graph
        self.Nmonte_points=Nmonte_points
        self.error = error
        self.dr = 1 

        self.coverage = 0

        self.G = nx.Graph()
        self.G.add_nodes_from(['top','bottom','left','right'])

        self.Nnodes = 0
        self.radii = np.zeros(1,int)
        self.radii2 = np.zeros(1,int)
        
        self.nodes = np.random.random(2).reshape(1,2) * self.size
        self.Nnodes = 1
        
        self.distance_matrix = np.zeros((1,1))

    def simulate(self):
        path = False #either a path from top to bottom, or left to right
        nodes_to_add = 0
        while not path:
            if nodes_to_add:
                self.nodes, added = self.add_nodes(self.nodes,nodes_to_add)
                if added: 
                    self.distance_matrix = self.find_distances(added)
                    self.radii = np.append(self.radii,[0]*added)
                    self.radii2 = np.append(self.radii2,[0]*added)

            nodes_to_add = self.increment()
            
            if self.check_path(self.G,'top','bottom',{'left','right'}): break
            if self.check_path(self.G,'left','right',{'top','bottom'}): break

        self.monte_points = self.create_monte_points()       
        self.monte_distances2 = self.calc_monte_distances2(self.nodes,
                                                           self.monte_points)
        self.coverage = self.calc_monte_coverage()
        
        if self.error:
            self.radii -= self.dr
            self.radii2 = self.radii * self.radii
            if -1 in self.radii: raise Exception
            self.error = self.coverage - self.calc_monte_coverage()
            self.radii += self.dr
            self.radii2 = self.radii * self.radii

        if self.graph:
            with open('nodes.dat','w') as f:
                for i in range(self.Nnodes):
                    r = self.radii[i]
                    if r != 0:
                      f.write(str(self.nodes[i][0]/self.size)+'\t'+
                            str(self.nodes[i][1]/self.size)+'\t'+
                            str(float(r)/self.size)+'\n')
            with open('nodes1.dat','w') as f:
                for i in range(self.Nnodes):
                    r = self.radii[i]-1
                    if r != 0:
                      f.write(str(self.nodes[i][0]/self.size)+'\t'+
                            str(self.nodes[i][1]/self.size)+'\t'+
                            str(float(r)/self.size)+'\n')

    def check_path(self,graph,source,target,ignore):
        sub_graph = graph.subgraph( set(graph.nodes) - ignore)
        if nx.has_path(sub_graph,source,target):
            path = True
            if self.graph:
                spath = nx.shortest_path(sub_graph,source,target)
                with open('path.dat','w') as f:
                    for node in [self.nodes[i]/self.size for i in spath[1:-1]]:
                        f.write(str(node[0])+'\t'+str(node[1])+'\n')
        else:
            path = False
        return path
            
    def create_monte_points(self):
        N = self.Nmonte_points 
        points = np.random.rand(N,2)
        return points * self.size
    
    def calc_monte_distances2(self, nodes, points):
        return np.sum((nodes[:, np.newaxis,:] - points[np.newaxis, :, :])**2,2)

    def calc_monte_coverage(self):
        coverage_matrix = self.monte_distances2 < self.radii2[:,np.newaxis]
        coverage = np.sum(coverage_matrix,0) > 0
        return float(np.sum(coverage)) / self.Nmonte_points

    def increment(self):
        self.radii += self.dr
        self.radii2 = self.radii * self.radii
        #if len(self.radii) != self.Nnodes: raise Exception(self.Nnodes,self.radii)
        self.touch_matrix = self.circles_touching()
        self.G.add_edges_from( np.transpose(np.where(self.touch_matrix==1)) )
        self.update_touching_boundary()
        add = np.random.poisson( float(self.rate) / self.size) 
        return add
        
    def update_touching_boundary(self):
        for i in range(self.Nnodes):
            x = self.nodes[i][0]
            y = self.nodes[i][1]
            r = self.radii[i]
            if y - r < 0:
                self.G.add_edge('bottom',i)
            if y + r > self.size:
                self.G.add_edge('top',i)
            if x - r < 0:
                self.G.add_edge('left',i)
            if x + r > self.size:
                self.G.add_edge('right',i)

    def find_distances(self,added):
        new_nodes = self.nodes[-added:]
        new_dists = np.sum((self.nodes[:,np.newaxis,:]-
                            new_nodes[np.newaxis,:,:]   )**2,2)
        dists = np.hstack((self.distance_matrix,new_dists[:self.Nnodes-added]))
        dists = np.vstack((dists,new_dists.T))
        return dists
        #return np.sum((self.nodes[:,np.newaxis,:]-self.nodes[np.newaxis,:,:])**2,2) 

    def circles_touching(self):
        radius_matrix = self.radii + self.radii[:,np.newaxis] 
        radius_matrix = radius_matrix**2
        np.fill_diagonal(radius_matrix,0)
        touch_matrix = radius_matrix > self.distance_matrix
        return touch_matrix

    def add_nodes(self, nodes, N):
        new_nodes = np.random.random(2*N).reshape(N,2) * self.size
        dists = np.sum((nodes[:, np.newaxis,:] - new_nodes[np.newaxis, :, :])**2,2)
        not_to_add = np.any( dists < self.radii2[:,np.newaxis],0)
        nodes = np.vstack(( nodes, new_nodes[np.where(not_to_add==0)] ))
        added = N-np.sum(not_to_add)
        self.Nnodes += added
        return nodes, added

    def print_output(self):
        print 'Coverage   =',self.coverage
        print 'Nsites     =',self.Nnodes
        print 'Max radius =',self.radii[0]
        if self.error is not False:
            print 'Error      =',self.error
        #print 'Niter      =',self.radii[0]

