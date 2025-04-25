class Node:
    '''
        A node in a doubly linked list
    '''
    
    def __init__(self, data, next_node=None, prev_node=None):
        self.data = data
        self.next_node = next_node
        self.prev_node = prev_node
        
    def setNextNode(self, next_node):
        self.next_node = next_node
        
    def getNextNode(self):
        return self.next_node
    
    def setPrevNode(self, prev_node):
        self.prev_node = prev_node
        
    def getPrevNode(self):
        return self.prev_node
    
    def printData(self):
        return self.data.printData()
    
    def getData(self):
        return self.data
    
    def setData(self, new_data):
        self.data = new_data


class CommandList:
    '''
        A doubly linked list, with head and tail nodes
    '''
    
    def __init__(self):
        self.head_node = None
        self.tail_node = None
  
    def addToHead(self, new_value):
        new_head = Node(new_value)
        current_head = self.head_node

        if current_head is not None:
            current_head.setPrevNode(new_head)
            new_head.setNextNode(current_head)

        self.head_node = new_head

        if self.tail_node is None:
            self.tail_node = new_head


    def addToTail(self, new_value):
        new_tail = Node(new_value)
        current_tail = self.tail_node

        if current_tail is not None:
            current_tail.setNextNode(new_tail)
            new_tail.setPrevNode(current_tail)

        self.tail_node = new_tail

        if self.head_node is None:
            self.head_node = new_tail


    def removeHead(self):
        removed_head = self.head_node

        if removed_head is None:
            return None

        self.head_node = removed_head.getNextNode()

        if self.head_node is not None:
            self.head_node.setPrevNode(None)

        if removed_head == self.tail_node:
            self.removeTail()

        return removed_head.getData()


    def removeTail(self):
        removed_tail = self.tail_node

        if removed_tail is None:
            return None

        self.tail_node = removed_tail.getPrevNode()

        if self.tail_node is not None:
            self.tail_node.setNextNode(None)

        if removed_tail == self.head_node:
            self.removeHead()

        return removed_tail.getData()


    def removeByValue(self, value_to_remove):
        node_to_remove = None
        current_node = self.head_node

        while current_node is not None:
            if current_node.get_value() == value_to_remove:
                node_to_remove = current_node
                break

        current_node = current_node.getNextNode()

        if node_to_remove is None:
            return None

        if node_to_remove == self.head_node:
            self.removeHead()
        elif node_to_remove == self.tail_node:
            self.removeTail()
        else:
            next_node = node_to_remove.getNextNode()
            prev_node = node_to_remove.getPrevNode()
            next_node.setPrevNode(prev_node)
            prev_node.setNextNode(next_node)

        return node_to_remove


    def printList(self):
        current_node = self.head_node

        while current_node is not None:
            current_node.printData()
            current_node = current_node.getNextNode()

class ActionChunk:
    '''
        Initialize a new instance of the class with the given value.

        Args:
            value (Any): The value to initialize the instance with.

        Attributes:
            time (Any): The time attribute of the instance.
            action (Any): The action attribute of the instance.
            text (Any): The text attribute of the instance.
            json (Any): The json attribute of the instance.
    '''

    def __init__(self, action_id, time, duration_min, energy, key, text = None, json = None, in_eclipse = None, eclipse_num = None, exposure_type = None):
        self.action_id = action_id
        self.time = time
        self.duration_min = duration_min
        self.energy = energy
        self.key = key
        self.text = text
        self.json = json
        if in_eclipse is None:
            in_eclipse = False
            eclipse_num = None
        self.in_eclipse = in_eclipse
        self.eclipse_num = eclipse_num
        self.exposure_type = exposure_type

    def printData(self):
        print(f'ID = {self.action_id}',
              f'Time = {self.time}',
              f'Duration [min]= {self.duration_min}',
              f'Energy = {self.energy}',
              f'ActionChunk = {self.key}',
              f'Text = {self.text}',
              f'Json = {self.json}',
              f'In Eclipse = {self.in_eclipse}',
              f'Eclipse Num = {self.eclipse_num}')
        print()

    def setJsonText(self, json):
        self.json = json

    def getJsonText(self):
        return self.json

    def setKey(self, key):
        self.key = key

    def getKey(self):
        return self.key

    def setTime(self, time):
        self.time = time

    def getTime(self):
        return self.time

    def getDuration(self):
        return self.duration_min

    def setDuration(self, duration):
        self.duration_min = duration

    def getEnergy(self):
        return self.energy

    def setEnergy(self, energy):
        self.energy = energy

    def setText(self, text):
        self.text = text

    def getText(self):
        return self.text

    def getInEclipse(self):
        return self.in_eclipse

    def setInEclipse(self, in_eclipse):
        self.in_eclipse = in_eclipse

    def setInEclipseNum(self, eclipse_num):
        self.eclipse_num = eclipse_num

    def getInEclipseNum(self):
        return self.eclipse_num

    def getEclipseNum(self):
        return self.eclipse_num

    def setEclipseNum(self, eclipse_num):
        self.eclipse_num = eclipse_num
