from xml.etree import ElementTree
from bs4 import BeautifulSoup
import nltk
import json
import re


class Parser:
    def __init__(self, path):
        self.entity_mentions = []
        self.event_mentions = []
        self.sentences = []

        self.entity_mentions, self.event_mentions, self.value_tag = self.parse_xml(path + '.apf.xml')
        self.sents_with_pos, self.full_doc = self.parse_sgm(path + '.sgm')
        self.event_mentions = self.get_head4arg(self.event_mentions, self.entity_mentions)
        self.modifyCollapseEntity()

    def get_head4arg(self, events, entities):

        dict_entities = dict()
        for entity in entities:
            dict_entities.update({entity['entity-id'] : [entity['text'], entity['position'], entity['entity-type']]})
        for ev in range(len(events)):
            for ar in range(len(events[ev]['arguments'])):
                entity_ = dict_entities[events[ev]['arguments'][ar]['entity-id']]
                events[ev]['arguments'][ar]['extent-text'] = events[ev]['arguments'][ar]['text']
                events[ev]['arguments'][ar]['text'] = entity_[0]
                events[ev]['arguments'][ar]['entity-type'] = entity_[2]
        return events


    def modifyCollapseEntity(self):
        map_changed = dict()
        count = 0
        for i, entity in enumerate(self.entity_mentions):
            for j, entity2 in enumerate(self.entity_mentions):
                if i < j:
                    range_1 = set(range(entity['position'][0], entity['position'][1]+1))
                    range_2 = set(range(entity2['position'][0], entity2['position'][1]+1))
                    collapse = range_1 & range_2
                    if len(collapse):

                        merged_string = self.merge2string(entity, entity2)
                        self.entity_mentions[i]['text'] = merged_string[0]
                        self.entity_mentions[i]['position'] = [merged_string[1], merged_string[2]]
                        map_changed[entity2['entity-id']] = entity['entity-id']
                        del self.entity_mentions[j]
                        count +=1


        print('->found {} intersecting cases'.format(count))
        for ide, event in enumerate(self.event_mentions):
            for ida, arg in enumerate(event['arguments']):
                if arg['entity-id'] in map_changed.keys():
                    self.event_mentions[ide]['arguments'][ida]['entity-id'] = map_changed[arg['entity-id']]


    def merge2string(self, entity, entity2):
        merged_entity = ''

        if entity['position'][0] <= entity2['position'][0]:
            merged_entity = entity['text']
            startMerge = entity['position'][1] - entity2['position'][0]
            for i, s in enumerate(entity2['text']):
                if i> startMerge:
                    merged_entity += s
        else:
            merged_entity = entity2['text']
            startMerge = entity2['position'][1] - entity['position'][0]
            for i, s in enumerate(entity['text']):
                if i> startMerge:
                    merged_entity += s

        return merged_entity, min(entity['position'][0], entity2['position'][0]), max(entity['position'][1], entity2['position'][1])


    def get_data(self):
        data = []

        def clean_text(text):
            # replace all newline to single whitespace
            return re.sub('\s+',' ', text.replace('\n', ' ')).strip()

        count = 0
        count_entity = 0
        list_found_entity = []
        list_found_event = []
        for id, sent in enumerate(self.sents_with_pos):
            item = dict()

            item['sentence'] = sent['text'].replace('\n', ' ')
            # check for empty line
            new_sent = re.sub('\s+',' ', item['sentence'])
            if new_sent ==' ':
                continue

            item['position'] = sent['position']
            text_position = sent['position']

            # reset start position for sentence with whitespace on the head
            for i, s in enumerate(item['sentence']):
                if s != ' ':
                    item['position'][0] += i
                    break

            item['sentence'] = new_sent.strip()

            entity_map_sent = dict()
            item['golden-entity-mentions'] = []
            item['golden-event-mentions'] = []

            # print('**sent: ', text_position, sent)

            for entity_mention in self.entity_mentions:
                entity_position = entity_mention['position']
                check_entity = False
                pos = sent['text'].find(entity_mention['text'])

                while(pos !=-1):
                    # if entity_mention['text'] =='petrel':
                    #     print(entity_mention['text'], pos, entity_position, text_position)

                    if (pos + text_position[0] - 10 < entity_position[0] and pos + text_position[0] >= entity_position[0]) or \
                        (pos + text_position[0] + 10 > entity_position[0] and pos + text_position[0] < entity_position[0]):
                        check_entity = True
                        break
                    else:
                        pos = sent['text'].find(entity_mention['text'], pos+1)

                # if text_position[0]-10 <= entity_position[0] and entity_position[1] <= text_position[1]+20:
                #     pos = sent['text'].find(entity_mention['text'])
                #
                #     if pos !=-1 and pos + text_position[0] < entity_position[0] +10:
                #         check_entity = True
                #
                # # elif id < len(self.sents_with_pos)-1:
                # #     if self.sents_with_pos[id+1]['position'][1] > entity_position[1] and entity_position[0]>= text_position[0]-5:
                # #         if len(nltk.word_tokenize(entity_mention['text'])) > 1 and sent['text'].find(entity_mention['text']) != -1 \
                # #                 and (self.sents_with_pos[id+1]['text'].find(entity_mention['text']) ==-1 or (self.sents_with_pos[id+1]['text'].find(entity_mention['text']) != 1 and self.sents_with_pos[id+1]['text'].find(entity_mention['text']) + self.sents_with_pos[id+1]['position'][0] > entity_position[0]+5)):
                # #             check_entity =True
                # #             print('!!!entity: ', entity_mention['text'],'-',entity_position, text_position)
                # #             # print(sent['text'])
                # #         elif entity_mention['text'] in nltk.word_tokenize(clean_text(sent['text'])) and (entity_mention['text'] not in nltk.word_tokenize(self.sents_with_pos[id+1]['text']) or self.sents_with_pos[id+1]['text'].find(entity_mention['text']) + self.sents_with_pos[id+1]['position'][0] > entity_position[0]+5):
                # #             check_entity = True
                # #             print('!!!entity: ', entity_mention['text'],'-',entity_position, text_position)
                # #             # print(sent['text'])
                # elif id < len(self.sents_with_pos)-1 and self.sents_with_pos[id+1]['position'][1] > entity_position[1] and entity_position[0]>= text_position[0]-5:
                #     if sent['text'].find(entity_mention['text']) != -1 \
                #             and (self.sents_with_pos[id+1]['text'].find(entity_mention['text']) ==-1 or (self.sents_with_pos[id+1]['text'].find(entity_mention['text']) != -1 and self.sents_with_pos[id+1]['text'].find(entity_mention['text']) + self.sents_with_pos[id+1]['position'][0] > entity_position[0]+5)):
                #         check_entity =True
                        # print('!!!entity: ', entity_mention['text'],'-',entity_position, text_position)

                # if entity_mention['text'] =='petrel':
                #     print(check_entity)
                if check_entity:
                    count_entity +=1
                    list_found_entity.append(entity_mention)
                    clean_entity = clean_text(entity_mention['text'])
                    # if len(clean_entity) <25:
                    item['golden-entity-mentions'].append({
                        'text': clean_entity,
                        'position': [pos, pos+ len(clean_entity) -1],
                        'entity-type': entity_mention['entity-type'],
                        'entity-id': entity_mention['entity-id']
                    })

                    #link current entity to the new position temporarily
                    entity_map_sent[entity_mention['entity-id']] = [clean_entity, pos, pos + len(clean_entity) -1]

            for event_mention in self.event_mentions:
                event_position = event_mention['trigger']['position']
                check_event = False
                # if sent['text'].find(event_mention['text'])!=-1:
                #     print(event_mention['trigger']['text'], event_mention['position'],'-',event_mention['trigger']['position'],'-',text_position)
                #     print(event_mention['text'])

                if text_position[0]-4 <= event_position[0] and text_position[0] <= event_position[1] and event_position[1] <= text_position[1]+8 and sent['text'].find(event_mention['text'])!=-1:
                    check_event = True

                elif id < len(self.sents_with_pos)-1:
                    if self.sents_with_pos[id+1]['position'][1]+3 > event_position[1] and event_position[0] >=text_position[0]  and sent['text'].find(event_mention['text']) != -1 and self.sents_with_pos[id+1]['text'].find(event_mention['text']) ==-1:
                        check_event = True
                        # print('!!!event: ', event_mention['trigger']['text'],'-',event_position,'-', text_position)
                        # print('sent:', sent['text'])
                        # print('next:',self.sents_with_pos[id+1]['text'])

                if check_event:
                    event_arguments = []
                    count +=1
                    list_found_event.append(event_mention)
                    # print('check event',count, event_mention['trigger']['text'])
                    for argument in event_mention['arguments']:
                        try:
                            event_arguments.append({
                            'role': argument['role'],
                            'text': entity_map_sent[argument['entity-id']][0],
                            'extent-text': clean_text((argument['extent-text'])),
                            'entity-type': argument['entity-type'],
                            'position': entity_map_sent[argument['entity-id']][1:],
                            'entity-id':argument['entity-id'],
                            })
                        except Exception as e:
                            print('error infor: ',e)
                            print('arg event error: ',argument['text'], argument['position'])
                            print('sent find',sent)
                            print('trigger: ', event_mention['trigger']['text'], ' ',event_mention['trigger']['position'],' ', text_position)


                    cleaned_trigger = clean_text(event_mention['trigger']['text'])
                    item['golden-event-mentions'].append({
                        'trigger': {'text': cleaned_trigger,
                                   'position': [event_mention['trigger']['position'][0],
                                                event_mention['trigger']['position'][0]+ len(cleaned_trigger)-1]
                                    },
                        'arguments': event_arguments,
                        'event_type': event_mention['event_type'],
                    })

            data.append(item)

        # check num event extracted
        print('\nFound Event: ',count,len(self.event_mentions))
        # print(list_found_event)
        # for event in self.event_mentions:
        #     if event not in list_found_event:
        #         print(event['text'])
        #         print(event['position'])

        print('Found entity: ', count_entity, len(self.entity_mentions),'\n')
        for entity in self.entity_mentions:
            if entity not in list_found_entity:
                print(entity['entity-id'], entity['text'], entity['position'])
        return data

    @staticmethod
    def parse_sgm(sgm_path):
        with open(sgm_path, 'r') as f:
            soup = BeautifulSoup(f.read(), features='html5lib')
            # text to get the original position
            sgm_text = soup.text.replace("&", '&amp;')
            doc_type = soup.doc.doctype.text
            def remove_tags(selector):
                tags = soup.findAll(selector)
                for tag in tags:
                    tag.extract()

            if doc_type == ' WEB TEXT ':
                remove_tags('poster')
                remove_tags('postdate')
            elif doc_type in [' CONVERSATION ', ' STORY ']:
                remove_tags('speaker')

            sents = []
            # text after remove some tags
            converted_text_ori = soup.text.replace("&", '&amp;')
            # ambiguous case for sentence tokenize (rebuild after sentence tokenize
            converted_text = converted_text_ori.replace("f.", "f .").replace('U.S.', 'U.S<dot>').replace('p.m.', 'p.m<dot>')\
                .replace('a.m.','a.m<dot>').replace('U.N.', 'U.N<dot>').replace('u.n.','u.n<dot>').replace('u.s.', 'u.s<dot>')\
                .replace('p.o.w.','p.o.w<dot>').replace('germ.','germ<dot>').replace('dr.','dr<dot>').replace('s.S','s. S')\
                .replace('mt.','mt<dot>').replace('Gov.','Gov<dot>').replace('.44','. 44').replace('.Arafat','. Arafat')\
                .replace('.Senior','. Senior').replace('.Judy', '. Judy').replace("w.''", 'w<mod>').replace('Sen.','Sen<mod> .')\
                .replace('1998.', '1998<mod> .').replace('1980.', '1980<mod> .').replace('2000.', '2000<mod> .')\
                .replace('1985.','1985<mod> .').replace('2001.', '2001<mod> .')

            # split double newline(equal 2 paragraph)
            for sent in nltk.sent_tokenize(converted_text):
                sents.extend([s for s in sent.split('\n\n') if s!=''])

            sents = sents[1:]
            sents_with_pos = []
            last_pos = 0
            for sent in sents:
                sent = sent.replace('f .','f.').replace('U.S<dot>', 'U.S.').replace('p.m<dot>', 'p.m.').replace('a.m<dot>','a.m.')\
                    .replace('U.N<dot>', 'U.N.').replace('u.n<dot>','u.n.').replace('u.s<dot>','u.s.').replace('p.o.w<dot>','p.o.w.')\
                    .replace('w<mod>',"w.''").replace('germ<dot>','germ.').replace('dr<dot>','dr.').replace('mt<dot>','mt.')\
                    .replace('Gov<dot>','Gov.').replace('Sen<mod> .','Sen.').replace('1998<mod> .','1998.').replace('1980<mod> .','1980.')\
                    .replace('2000<mod> .','2000.').replace('1985<mod> .', '1985.').replace('2001<mod> .','2001.')
                if sent.find('Sen.') != -1:
                    print(sent)
                pos = sgm_text.find(sent, last_pos)
                last_pos = pos
                sents_with_pos.append({
                    'text':sent.replace('f.','f .').replace('-',' ').replace('/', '/ ').replace('~',' ').replace('U.S.', 'U.S ')\
                        .replace('p.m.', 'p.m ').replace('a.m.','a.m ').replace('U.N.', 'U.N ').replace('u.n.','u.n ')\
                        .replace('u.s.','u.s ').replace('p.o.w.','p.o.w ').replace('germ.','germ ').replace('dr.','dr').replace('mt.', 'mt ')\
                        .replace('Gov.', 'Gov ').replace('&amp;', "&"),
                    'position': [pos, pos + len(sent)-1]
                })
            # print(sents_with_pos)
            return sents_with_pos, converted_text_ori

    def parse_xml(self, xml_path):
        entity_mentions, event_mentions = [], []
        tree = ElementTree.parse(xml_path)
        root = tree.getroot()
        value_tags = set()
        for child in root[0]:
            if child.tag == 'entity':
                entity_mentions.extend(self.parse_entity_tag(child))
            elif child.tag in ['value', 'timex2']:
                if child.tag =='value':
                    for tag in self.parse_value_timex_tag(child):
                        value_tags.update([tag['entity-type']])
                entity_mentions.extend(self.parse_value_timex_tag(child))
            elif child.tag == 'event':
                event_mentions.extend(self.parse_event_tag(child))

        return entity_mentions, event_mentions, value_tags

    @staticmethod
    def parse_entity_tag(node):
        entity_mentions = []

        for child in node:
            if child.tag != 'entity_mention':
                continue
            extent = child[0]
            head = child[1]
            # charset = extent[0]
            charset = head[0]
            entity_mention = dict()
            entity_mention['entity-id'] = child.attrib['ID']
            entity_mention['entity-type'] = '{}:{}'.format(node.attrib['TYPE'], node.attrib['SUBTYPE'])
            entity_mention['text'] = charset.text.replace('f.','f .').replace('-',' ').replace('/', '/ ').replace('~',' ').replace('U.S.', 'U.S ')\
                                            .replace('p.m.', 'p.m ').replace('a.m.','a.m ').replace('U.N.', 'U.N ').replace('u.n.','u.n ')\
                                            .replace('u.s.','u.s ').replace('p.o.w.','p.o.w ').replace('germ.','germ ').replace('dr.','dr').replace('mt.', 'mt ')\
                                            .replace('Gov.', 'Gov ')
            entity_mention['position'] = [int(charset.attrib['START']), int(charset.attrib['END'])]
            entity_mentions.append(entity_mention)

        return entity_mentions

    @staticmethod
    def parse_event_tag(node):
        event_mentions = []
        for child in node:
            if child.tag == 'event_mention':
                event_mention = dict()
                event_mention['event_type'] = '{}:{}'.format(node.attrib['TYPE'], node.attrib['SUBTYPE'])
                event_mention['arguments'] = []
                for child2 in child:
                    if child2.tag == 'extent':
                        charset = child2[0]
                        event_mention['text'] = charset.text.replace('f.','f .').replace('-',' ').replace('/', '/ ').replace('~',' ').replace('U.S.', 'U.S ')\
                                                        .replace('p.m.', 'p.m ').replace('a.m.','a.m ').replace('U.N.', 'U.N ').replace('u.n.','u.n ')\
                                                        .replace('u.s.','u.s ').replace('p.o.w.','p.o.w ').replace('germ.','germ ').replace('dr.','dr').replace('mt.', 'mt ')\
                                                        .replace('Gov.', 'Gov ')
                        event_mention['position'] = [int(charset.attrib['START']), int(charset.attrib['END'])]
                    if child2.tag == 'anchor':
                        charset = child2[0]
                        event_mention['trigger'] = {
                            'text': charset.text.replace('f.','f .').replace('-',' ').replace('/', '/ ').replace('~',' ').replace('U.S.', 'U.S ')\
                                            .replace('p.m.', 'p.m ').replace('a.m.','a.m ').replace('U.N.', 'U.N ').replace('u.n.','u.n ')\
                                            .replace('u.s.','u.s ').replace('p.o.w.','p.o.w ').replace('germ.','germ ').replace('dr.','dr').replace('mt.', 'mt ')\
                                            .replace('Gov.', 'Gov '),
                            'position': [int(charset.attrib['START']), int(charset.attrib['END'])],
                        }
                    if child2.tag == 'event_mention_argument':
                        extent = child2[0]
                        charset = extent[0]
                        event_mention['arguments'].append({
                            'text': charset.text.replace('f.','f .').replace('-',' ').replace('/', '/ ').replace('~',' ').replace('U.S.', 'U.S ')\
                                            .replace('p.m.', 'p.m ').replace('a.m.','a.m ').replace('U.N.', 'U.N ').replace('u.n.','u.n ')\
                                            .replace('u.s.','u.s ').replace('p.o.w.','p.o.w ').replace('germ.','germ ').replace('dr.','dr').replace('mt.', 'mt ')\
                                            .replace('Gov.', 'Gov '),
                            'position': [int(charset.attrib['START']), int(charset.attrib['END'])],
                            'role': child2.attrib['ROLE'],
                            'entity-id': child2.attrib['REFID']
                        })
                event_mentions.append(event_mention)
        return event_mentions

    @staticmethod
    def parse_value_timex_tag(node):
        entity_mentions = []

        for child in node:
            extent = child[0]
            charset = extent[0]

            val_tim_mention = dict()
            val_tim_mention['entity-id'] = child.attrib['ID']

            if 'TYPE' in node.attrib:
                val_tim_mention['entity-type'] = node.attrib['TYPE']
            if 'SUBTYPE' in node.attrib:
                val_tim_mention['entity-type'] += ':{}'.format(node.attrib['SUBTYPE'])
            if child.tag == 'timex2_mention':
                val_tim_mention['entity-type'] = 'TIM:time'

            val_tim_mention['text'] = charset.text.replace('f.','f .').replace('-',' ').replace('/', '/ ').replace('~',' ').replace('U.S.', 'U.S ')\
                                            .replace('p.m.', 'p.m ').replace('a.m.','a.m ').replace('U.N.', 'U.N ').replace('u.n.','u.n ')\
                                            .replace('u.s.','u.s ').replace('p.o.w.','p.o.w ').replace('germ.','germ ').replace('dr.','dr').replace('mt.', 'mt ')\
                                            .replace('Gov.', 'Gov ')
            val_tim_mention['position'] = [int(charset.attrib['START']), int(charset.attrib['END'])]

            entity_mentions.append(val_tim_mention)

        return entity_mentions

