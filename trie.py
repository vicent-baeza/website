
class Trie:
    def __init__(self):
        self.is_leaf = False
        self.count = 0
        self.children: dict[str, Trie] = {}

    def add(self, word: str):
        self.count += 1
        if len(word) == 0:
            self.is_leaf = True
            return
        if word[0] not in self.children:
            self.children[word[0]] = Trie()
        self.children[word[0]].add(word[1:])
    
    def json(self):
        content = ''
        if len(self.children) > 0:
            json_list = ','.join([f'"{s}": {c.json()}"' for s, c in self.children.items()])
            content += f'"children": [{json_list}]'
            if self.is_leaf:
                content += ',"leaf": true'
        elif not self.is_leaf:
            return ''
        
        return '{' + content + '}'

