from . import helpers
from . import ilp
from . import ch

class Algorithm:
    
    """Class to select algorithm for solving the subproblems.
    
    Attributes:
        algorithm_name (string): Name of selected algorithm. 
            Options: \"ILP\", \"CH\". 
            Default: \"ILP\".
        ilp_time_limit (float): Time limit for algorithm \"ILP\" in seconds. 
            If <= 0, no time limit is enforced. 
            Default: 60.
        ilp_tune (bool): If True, the model generated by \"ILP\" is tuned before being optimized. 
            Default: False.
        ch_alpha (float): Between 0 and 1. If smaller than 1, the algorithm behaves non-deterministically.
            Default: 1.0.
        ch_seed (None or int): Seed for random generation. 
            Default: None.
    """
    
    def __init__(self):
        self.algorithm_name = "ILP"
        self.ilp_time_limit = 60
        self.ilp_tune = False
        self.ch_alpha = 1.0
        self.ch_seed = None
    
    def use_ilp(self, time_limit = 60, tune = False):
        """Use the algorithm \"ILP\".
            
        Args:
            time_limit (float): Time limit for algorithm \"ILP\" in seconds. If <= 0, no time limit is enforced.
            tune (bool): If True, the model generated by \"ILP\" is tuned before being optimized.
        """
        self.algorithm_name = "ILP"
        self.ilp_time_limit = time_limit
        self.ilp_tune = tune
    
    def use_ch(self, alpha = 1.0, seed = None):
        """Use the algorithm \"CH\".
        """
        self.algorithm_name = "CH"
        self.ch_alpha = alpha
        self.ch_seed = seed
            
    def run(self, weights, subgraph):
        """Runs the selected algorithm on a given subgraph.
        
        Args:
            weights (numpy.array): The overall problem instance.
            subgraph (networkx.Graph): The subgraph of the instance that should be rendered bi-transitive.
        
        Returns:
            networkx.Graph: The obtained bi-transitive subgraph.
            float: Objective value of obtained solution.
            bool: True if and only if obtained solution is guaranteed to be optimal.
        """
        if self.algorithm_name == "ILP":
            return ilp.run(weights, subgraph, self.ilp_time_limit, self.ilp_tune)
        elif self.algorithm_name == "CH":
            return ch.run(weights, subgraph, self.ch_alpha, self.ch_seed)
        else:
            raise Exception("Invalid algorithm name \"" + self.algorithm_name + "\". Options: \"ILP\", \"CH\".")
    
    
def compute_bi_clusters(weights, algorithm):
    """Computes bi-clusters using bi-cluster editing.
    
    Given a matrix W = (w[i][k]) of weights of dimension n x m with positive and negative 
    entries, the bi-cluster editing problem asks to transform the bipartite graph
    ([n], [m], E) into a collection of disjoint bi-cliques by adding or deleting edges:
        - The edge set E contains all (i,k) with w[i][k] > 0.
        - Adding an edge induces the cost -w[i][k].
        - Deleting an edge induces the cost w[i][k].
        - The overall induced cost should be minimized.
    
    The function first decomposes the instance into connected components and 
    checks whether they are already bi-cliques. Subsequently, it calls a 
    user-specified algorithm to solve the remaining subproblems.
    
    Args:
        weights (numpy.array): The problem instance.
        algorithm (Algorithm): The subgraph that should be rendered bi-transitive.
    
    Returns:
        list of tuple of list of int: List of computed bi-clusters. 
            The first element of each bi-cluster is the list of rows, the second the list of columns.
        float: Objective value of the obtained solution.
        bool: True if and only if the obtained solution is guaranteed to be optimal.
    """
    
    # Get dimension of the problem instance and build NetworkX graph.
    num_rows = weights.shape[0]
    num_cols = weights.shape[1]
    graph = helpers.build_graph_from_weights(weights, range(num_rows + num_cols))
    
    # Initialize the return variable.
    bi_clusters = []
    
    # Decompose graph into connected components and check if some 
    # of them are already bi-cliques. If so, put their rows and columns 
    # into bi-clusters. Otherwise, add the connected 
    # component to the list of connected subgraphs that have to be 
    # rendered bi-transitive.
    subgraphs = []
    components = helpers.connected_components(graph)
    for component in components:
        if helpers.is_bi_clique(component, num_rows):
            bi_cluster = ([], [])
            for node in component.nodes:
                if helpers.is_row(node, num_rows):
                    bi_cluster[0].append(node)
                else:
                    bi_cluster[1].append(helpers.node_to_col(node, num_rows))
            bi_clusters.append(bi_cluster)
        else:
            subgraphs.append(component)
            
    # Print information about connected components.
    print("\n==============================================================================")
    print("Finished pre-processing.")
    print("------------------------------------------------------------------------------")
    print("Number of connected components: " + str(len(components)))
    print("Number of bi-cliques: " + str(len(bi_clusters)))
    print("==============================================================================")
    
    # Solve the subproblems and construct the final bi-clusters. 
    # Also compute the objective value and a flag that indicates whether the
    # obtained solution is guaranteed to be optimal.
    obj_val = 0
    is_optimal = True 
    counter = 0
    for subgraph in subgraphs:
        counter = counter + 1
        print("\n==============================================================================")
        print("Solving subproblem " + str(counter) + " of " + str(len(subgraphs)) + ".")
        print("------------------------------------------------------------------------------")
        n = len([node for node in subgraph.nodes if helpers.is_row(node, num_rows)])
        m = len([node for node in subgraph.nodes if helpers.is_col(node, num_rows)])
        print("Dimension: " + str(n) + " x " + str(m))
        bi_transitive_subgraph, local_obj_val, local_is_optimal = algorithm.run(weights, subgraph)
        obj_val = obj_val + local_obj_val
        is_optimal = is_optimal and local_is_optimal
        for component in helpers.connected_components(bi_transitive_subgraph):
            if not helpers.is_bi_clique(component, num_rows):
                msg = "Subgraph should be bi-clique but isn't."
                msg = msg + "\nNodes: " + str(component.nodes)
                msg = msg + "\nEdges: " + str(component.edges)
                raise Exception(msg)
            bi_cluster = ([], [])
            for node in component.nodes:
                if helpers.is_row(node, num_rows):
                    bi_cluster[0].append(node)
                else:
                    bi_cluster[1].append(helpers.node_to_col(node, num_rows))
            bi_clusters.append(bi_cluster)
        print("==============================================================================")
    
    print("\n==============================================================================")
    print("Finished computation of bi-clusters.")
    print("------------------------------------------------------------------------------")
    print("Objective value: " + str(obj_val))
    print("Is optimal: " + str(is_optimal))
    print("Number of bi-clusters: " + str(len(bi_clusters)))
    print("==============================================================================")
    
    
    # Return the obtained bi-transitive subgraph, the objective value of the obtained solution, 
    # and a flag that indicates if the solution is guaranteed to be optimal.
    return bi_clusters, obj_val, is_optimal 
    
def save_bi_clusters_as_xml(filename, bi_clusters, obj_val, is_optimal, instance = ""):
    """Saves bi-clusters as XML file.
    
    Args:
        filename (string): Name of XML file.
        bi_clusters (list of tuple of list of int): List of computed bi-clusters.
            The first element of each bi-cluster is the list of rows, the second the list of columns.
        obj_val (float): Objective value of the obtained solution.
        is_optimal (bool): Set to True if and only if the obtained solution is guaranteed to be optimal.
        instance (string): String that contains information about the problem instance.
    """
    elem_tree = helpers.build_element_tree(bi_clusters, obj_val, is_optimal, instance)
    xml_file = open(filename, "w")
    xml_file.write(helpers.prettify(elem_tree))
    xml_file.close()
    
