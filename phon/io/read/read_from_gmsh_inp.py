__copyright__ = "Copyright (C) 2013 Kristoffer Carlsson"

__license__ = """
Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
"""

"""
Module that contains the method of reading a mesh from a .inp file
generated by Neper.
"""

import re

from phon.mesh_objects.element import Element
from phon.mesh_objects.node import Node
from phon.mesh_objects.mesh import Mesh

from phon.mesh_objects.element_set import ElementSet
from phon.mesh_objects.element_side_set import ElementSideSet
from phon.mesh_objects.element_side_set import ElementSide
from phon.mesh_objects.node_set import NodeSet

import numpy.linalg


def read_from_gmsh_inp(basename, ngrains, verbose=0):
    """
    Reads a sequence of grains from *.msh-files generated by GMsh (and Dream3D) and stores it into a 
    Mesh class object.
    
    :param filename: The base name of the files sequence from where to read the mesh from.
    :type filename: string
    :param verbose: Determines what level of print out to the console.
    :type verbose: 0, 1 or 2
    :return: A mesh class containing the read mesh objects.
    :rtype: :class:`Mesh`
    :raises ReadInpFileError: If specific syntax error are found.
    
    """
    mesh = Mesh("grains")
    for grainid in range(1, ngrains):
        filename = basename + str(grainid) + ".msh"
        print("Reading grain " + str(grainid))
        grainmesh = Mesh("grain" + str(grainid))
        with open(filename, "rU") as f:
            # Read mesh objects
            num_elems = 0
            while True:
                keyword = f.readline().strip()
                if keyword == "$Nodes":
                    print("Reading nodes")
                    _read_nodes(f, grainmesh, verbose)
                elif keyword == "$Elements":
                    print("Reading elements")
                    _read_elements(f, grainmesh, verbose)
                    break

        f.close()
        print("Merging grain")
        _merge_mesh(mesh, grainmesh, grainid)
    # create grain boundaries
    # remove duplicate nodes
    # create boundary sets
    return mesh


def _construct_node2element(mesh):
    node2elements = [list() for n in range(0,len(mesh.nodes))]
    for element_id, element in mesh.elements.iteritems():
        for n in element.vertices:
            node2elements[n].append(element_id)
    return node2elements

def _merge_mesh(mesh, grainmesh, grainid):
    # Need these to append new nodes and elements:
    elemcount = 0
    if len(mesh.elements) > 0:
        elemcount = max(mesh.elements.keys())
    nodecount = 0
    if len(mesh.nodes) > 0:
        nodecount = max(mesh.nodes.keys())

    # Find duplicate nodes
    node_merge_list = dict()
    node2node = dict()
    for node_id1, node1 in grainmesh.nodes.iteritems():
        found = False
        for node_id2, node2 in mesh.nodes.iteritems():
            dist = numpy.linalg.norm([node1.x - node2.x, node1.y - node2.y, node1.z - node2.z])
            if dist < 1e-6:
                node_merge_list[node_id1] = node_id2
                #found = True
                break
        if found:
            node2node[node_id1] = node_merge_list[node_id1]
        else:
            nodecount += 1
            node2node[node_id1] = nodecount

    #node2elements1 = _construct_node2element(grainmesh)
    node2elements2 = _construct_node2element(mesh)

    
    """
    # Find only elements in grainmesh that should have a matching surface;
    for e1, elem1 in grainmesh.elements.iteritems():
        v1 = elem1.vertices # Nodes numbers in "grainmesh"
        v2 = [node_merge_list[v] for v in v1 if v in node_merge_list] # Node numbers in "mesh"
        if len(v2) == 0:
            continue
        e = [mesh.elements[v] for v in v2] # Elements connected to corresponding nodes in "mesh"

        # Check for surfaces, and if so, add them to a set
        # TODO: Need to differentiate between grainid-grainid here and create different sets
        # Right now, I just add triangular elements.
        if v1[0] in node_merge_list and v1[1] in node_merge_list and v1[3] in node_merge_list:
            s1 = 1
            e2 = iter(set(e[0]) & set(e[1]) & set(e[2])).next()
            surfelem = Element("CPE3", [v2[0], v2[1], v2[3]])
            elemcount += 1
            mesh.elements[elemcount] = surfelem
        if v1[0] in node_merge_list and v1[2] in node_merge_list and v1[1] in node_merge_list:
            s1 = 2
            e2 = iter(set(e[0]) & set(e[2]) & set(e[1])).next()
            surfelem = Element("CPE3", [v2[0], v2[2], v2[1]])
            elemcount += 1
            mesh.elements[elemcount] = surfelem
        if v1[0] in node_merge_list and v1[3] in node_merge_list and v1[2] in node_merge_list:
            s1 = 3
            e2 = iter(set(e[0]) & set(e[3]) & set(e[2])).next()
            surfelem = Element("CPE3", [v2[0], v2[3], v2[2]])
            elemcount += 1
            mesh.elements[elemcount] = surfelem
        if v1[1] in node_merge_list and v1[2] in node_merge_list and v1[3] in node_merge_list:
            s1 = 4
            e2 = iter(set(e[1]) & set(e[2]) & set(e[3])).next()
            surfelem = Element("CPE3", [v2[1], v2[2], v2[3]])
            elemcount += 1
            mesh.elements[elemcount] = surfelem
    """

    # Add the nodes from "grainmesh" to "mesh"
    for node_id1, node1 in grainmesh.nodes.iteritems():
        mesh.nodes[node2node[node_id1]] = node1

    # Add the elements from "grainmesh" to "mesh"
    for elem1 in grainmesh.elements.values():
        # Renumber vertices to new combined mesh;
        elem1.vertices = [node2node[v] for v in elem1.vertices]
        elemcount += 1
        mesh.elements[elemcount] = elem1

def _read_nodes(f, mesh, verbose):
    nnodes = int(f.readline())
    while True:
    	line = f.readline().strip()
        if line == "$EndNodes":
            return;

        words = line.split()
        num = int(words[0])
        coord = list(map(float, words[2:]))
        node = Node(*coord)
        mesh.nodes[num] = node

def _read_elements(f, mesh, verbose):
    """Reads elements from the file.
    :param f: The file from where to read the elements from.
    :type f: file object at the elements
    :param mesh: Mesh to insert the read elements into.
    :type mesh: :class:`Mesh`
    :param verbose: Determines what level of print out to the console.
    :type verbose: 0, 1 or 2
    :return: Nothing, but has the side effect of setting the pointer
             in the file object f to the line with the next keyword.
    """
    nelems = int(f.readline())
    while True:
    	line = f.readline().strip()
        if line == "$EndElements":
            return;

        words = line.split()
        num = int(words[0])
        elem_nodes = list(map(int, words[-3:]))
        element = Element("CS4", elem_nodes)
        mesh.elements[num] = element

class ReadMshFileError(Exception):
    """
    Base class for errors in the :mod:`read_from_neper_inp` module.

    """

    def __init__(self, status):
        """Creates an exception with a status."""
        Exception.__init__(self, status)
        self.status = status

    def __str__(self):
        """Return a string representation of the :exc:`ReadInpFileError()`."""
        return str(self.status)

