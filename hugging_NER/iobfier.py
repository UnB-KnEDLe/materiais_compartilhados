from tqdm import tqdm

class IOBfier:
    
    def __init__(self, tokenize, knedle_dataset=True, text_column='texto', schema='iob', sep='-||-'):
        self.tokenize = tokenize
        self.schema = schema
        self.sep = sep
        self.text_column = text_column
        self.knedle_dataset = knedle_dataset
        
    def remove_internal_ranges(self, intervalos):
        removidos = []
        for i in range(len(intervalos)):        
            for j in range(len(intervalos)):
                if i != j and intervalos[i][1][0] >= intervalos[j][1][0] and intervalos[i][1][1] <= intervalos[j][1][1]:
                    removidos.append(intervalos[i])                    
                    break
        for r in removidos:            
            intervalos.remove(r)

    def find_str(self, txt, subtxt):    
        initial_position = txt.find(subtxt)
        final_position = initial_position + len(subtxt)
        return (initial_position, final_position)

    def find_row(self, row, columns):
        text = row[self.text_column]
        pos_pairs = []
        for column in columns:
            if isinstance(row[column],str) and column is not self.text_column:
                data = row[column].split('-||-')
                if len(data) == 1:
                    pos = self.find_str(text, data[0])
                    pos_pairs.append((column, pos))
                elif len(data) > 1:                    
                    for str_data in data:
                        pos = self.find_str(text, str_data)
                        pos_pairs.append((column, pos))
        return pos_pairs

    def tagg_entity(self, text, entity_name):
        # implemented only for iob schmea
        labels = []
        words = []
        for i, word in enumerate(self.tokenize(text)):
            if self.schema.lower() == 'iob':
                if i == 0:
                    labels.append('B-'+entity_name)
                else:
                    labels.append('I-'+entity_name)        
                words.append(word)
        return words, labels

    def create_IOB_from_text(self, text, pos_pairs):
        pos_pairs = sorted(pos_pairs, key=lambda x: x[1][0])
        self.remove_internal_ranges(pos_pairs)
        dict_masks = {}
        cp_text = str(text)
        for i, pos in enumerate(reversed(pos_pairs)):
            xxmask = 'xxmaskxx' + str(i)
            cp_text = cp_text[:pos[1][0]] + ' ' + xxmask + ' ' +cp_text[pos[1][1]+1:]
            dict_masks[xxmask] = pos    
    
        labels = []
        words = []
        for i, word in enumerate(self.tokenize(cp_text)):        
            if word in dict_masks.keys():
                sub_text = text[dict_masks[word][1][0]:dict_masks[word][1][1]]            
                tagg_words, tagg_labels = self.tagg_entity(sub_text, dict_masks[word][0])   
                words += tagg_words
                labels += tagg_labels
            else:
                labels.append('O')
                words.append(word)
        return words, labels   
    
    def rotate_df(self, df, act):
        df_aux = df.pivot_table(index=['id_ato'], columns=['tipo_ent'], 
                                values=self.text_column, aggfunc=lambda x: self.sep.join(x))
        df_aux.rename({act:self.text_column}, axis=1, inplace=True)
        df_aux = df_aux[~df_aux[self.text_column].isnull() ]
        return df_aux
    
    # act = 'EXTRATO_CONTRATO'
    def transform(self, df, act):
        if self.knedle_dataset:
            df = self.rotate_df(df, act)
        columns = df.columns
        words = []
        labels = []        
        
        for index, row in tqdm(df.iterrows(), total=df.shape[0], desc='Creating IOB'):
            pos_pairs = self.find_row(row, columns)    
            ws, ls = self.create_IOB_from_text(row[self.text_column], pos_pairs)
            words.append(ws)
            labels.append(ls)
        return words, labels