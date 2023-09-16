import copy
import json
import logging
import os

from stanfordcorenlp import StanfordCoreNLP
from parserACE import Parser
import argparse
from tqdm import tqdm


def get_data_paths(ace2005_path):
    test_files, dev_files, train_files = [], [], []

    with open('./data_list.csv', mode='r') as csv_file:
        rows = csv_file.readlines()
        for row in rows[1:]:
            items = row.replace('\n', '').split(',')
            data_type = items[0]
            name = items[1]

            path = ace2005_path+name
            if data_type == 'test':
                test_files.append(path)
            elif data_type == 'dev':
                dev_files.append(path)
            elif data_type == 'train':
                train_files.append(path)
    return test_files, dev_files, train_files


def find_token_index(tokens, start_pos, end_pos, phrase):
    start_idx, end_idx = -1, -1
    check_after = True
    ori_start_pos = start_pos
    # print('start: ', start_pos)
    length_sent = tokens[-1]['characterOffsetEnd']
    check_start_match_list = [-1,]
    merge_phrase = ''.join(word for word in phrase.split() if word!='')
    while check_after:
        partial_phrase = ''
        start_add = -1
        for idx, token in enumerate(tokens):

            if merge_phrase.find(partial_phrase + ''.join(word for word in token['originalText'].split()))!=-1 or (partial_phrase + ''.join(word for word in token['originalText'].split())).find(merge_phrase) !=-1:
                partial_phrase += ''.join(word for word in token['originalText'].split())
            else:
                partial_phrase = ''.join(word for word in token['originalText'].split())
                start_add = -1


            # print('group: ', partial_phrase)
            if token['characterOffsetBegin'] <= start_pos and (token['originalText'].find(phrase) ==0 or phrase.find(token['originalText']) ==0) and start_add ==-1:
            # if token['characterOffsetBegin'] <= start_pos and (phrase.find(token['originalText'])!=-1 or (token['originalText'].find(phrase) !=-1)) and start_add ==-1:
                start_add = idx
                partial_phrase = ''.join(word for word in token['originalText'].split() if word !='')
                # print('start add: ', partial_phrase, idx)

            if partial_phrase.find(merge_phrase) != -1:
                if start_add !=-1:
                    check_start_match_list.append(start_add)
                    # print('check complete phrase', start_add)
                    check_after = False
                    partial_phrase = ''
                    start_add = -1


        if check_after:
            start_pos += 1

        if start_pos >= length_sent:
            for idx, token in enumerate(tokens):
                if token['characterOffsetBegin'] <= ori_start_pos and (
                        token['word'].lower().find(phrase.lower()) != -1 or phrase.lower().find(token['word'].lower()) != -1)\
                        and phrase.find(tokens[idx - 1]['word']) == -1:
                    start_idx = idx
            break
        '''
        - gốc: không lấy đươc entity với vị trí đầu có 1 ký tự
        - and 3 kiểm tra lỗi bị lệnh 1 vài ký tự về phí trc ~ idx bị đầy về phía sau
        - dùng while để xử lý lệch idx về phía trước
        
        '''
    # Some of the ACE2005 data has annotation position errors when tokenize.
    # print('check phrase:', json.loads(nlp.annotate(phrase,properties={'annotators': 'tokenize'}))['tokens'])
            # length = len(nlp.annotate(phrase,properties={'annotators': 'tokenize'})['tokens'])
    try:
        if len(check_start_match_list)>1:
            start_idx = check_start_match_list[-1]
            length = len(json.loads(nlp.annotate(phrase,properties={'annotators': 'tokenize'}))['sentences'][0]['tokens'])
            end_idx = start_idx + length
            word_check = ''
            status = False
            for i in range(start_idx, end_idx):
                # remove whitespace and merge all character in each token
                word_check += ''.join(w for w in tokens[i]['originalText'].split())

                if word_check.find(merge_phrase) != -1:
                    break
            while not status:
                if (merge_phrase in word_check) or (end_idx - start_idx - length) > 4:
                    status = True
                    # print('finish:', word_check, ' ', merge_phrase, ' ', start_pos, '', start_idx)
                else:
                    try:
                        word_check += ''.join(w for w in tokens[end_idx]['originalText'].split())
                    except Exception as e:
                        print(e)
                        print('!!' + ' '.join(token['originalText'] for token in tokens), '--', phrase, '--', ' < ', start_pos)
                        print(word_check, ' ', merge_phrase)
                    end_idx += 1

    except Exception as e:
        print(e)
        print('error entity: ',phrase)
        print(tokens)

    if end_idx> len(tokens)-1:
        end_idx = len(tokens)-1

    return start_idx, end_idx


def preprocessing(data_type, files, dep_type='basicDependencies'):
    event_count, entity_count, sent_count = 0, 0, 0
    result, result_conll_1, result_conll_2, result_conll_3= dict(), dict(), dict(), dict()
    time_value_tag = ['TIM:time', 'Contact-Info:URL', 'Numeric:Money', 'Sentence', 'Contact-Info:Phone-Number', 'Crime', 'Job-Title', 'Contact-Info:E-Mail', 'Numeric:Percent']
    print('-' * 20)
    print('[preprocessing] type: {} ({})'.format(data_type, len(files)))
    value_tags = set()
    id_doc = 0
    set_deps = set()
    tags = []
    for file in tqdm(files):
        print('==>',file)
        document_conll_NE_full = []
        document_conll_NE_short_ori = []
        document_conll_NE_short = []
        document_json = []
        # if "CNN_CF_20030303.1900.02" not in file:
        # # if "timex2norm/AFP_ENG_200300413.0250" not in file:
        #     continue
        parser = Parser(path=file)
        value_tags.update(parser.value_tag)
        entity_count += len(parser.entity_mentions)
        event_count += len(parser.event_mentions)
        sent_count += len(parser.sents_with_pos)
        tags.extend(parser.extracted_tags)
        if parser.check_headline():
            print("check--------->", file)
            for headline in parser.headlines:
                print(headline)

        continue

        id_tag = 0
        id_event = 0

        for item in parser.get_data():
            data = dict()
            data['sentence'] = item['sentence']
            data['golden-entity-mentions'] = []
            data['golden-event-mentions'] = []
            try:
                nlp_text = nlp.annotate(item['sentence'], properties={'annotators': 'tokenize, depparse'})
                nlp_res = json.loads(nlp_text)
            except Exception as e:
                print('StanfordCore Exception ', e)
                print('item["sentence"] :', item['sentence'])
                print('nlp_text :', nlp_text)
                print(file)
                continue
            if len(nlp_res['sentences']) > 1:
                logging.warning("2 sentence: {}| filename: {}".format(item['sentence'], file))
                start_next_sent = nlp_res['sentences'][0]['tokens'][-1]['index'] if len(nlp_res['sentences'][0]['tokens']) > 0 else 0
                curr_id = 0
                tokens = nlp_res['sentences'][0]['tokens']
                deps = nlp_res['sentences'][0][dep_type] # 'basicDependencies' 'enhancedDependencies' enhancedPlusPlusDependencies
                for sentence in nlp_res['sentences'][1:]:
                    for token in sentence['tokens']:
                        curr_id = token['index']
                        token['index'] = token['index'] + start_next_sent
                        tokens.append(token)
                    for dep in sentence['enhancedPlusPlusDependencies']:
                        if dep['dep'] != "ROOT":
                            dep['governor'] += start_next_sent

                        dep['dependent'] += start_next_sent
                        deps.append(dep)

                    start_next_sent += curr_id

            for sentence in nlp_res['sentences'][:1]:
                tokens = sentence['tokens']
                data['words'] = list(map(lambda x: x['originalText'], tokens))
                data[dep_type] = [{'governor': dep['governor'] - 1,
                                        'dependent': dep['dependent'] - 1,
                                        'governor_w': dep['governorGloss'],
                                        'dependent_w': dep['dependentGloss'],
                                        'dep': dep['dep']} for dep in sentence[dep_type]]
                set_deps.update([dep['dep'] for dep in sentence[dep_type]])
                sent_start_pos = item['position'][0]
                sentence_withNE = [[w,'O','O','O',[]] for w in data['words']]
                sentence_withNE_short_ori = [[w,'O','O','O',[]] for w in data['words']]
                sentence_withNE_short = [[w,'O','O','O',[]] for w in data['words']]

                # print('->sent:',data['sentence'])
                # print('  sent pos:', sent_start_pos)
                # print(tokens)

                for entity_mention in item['golden-entity-mentions']:
                    position = entity_mention['position']
                    start_idx, end_idx = find_token_index(
                        tokens=tokens,
                        start_pos=position[0],
                        end_pos=position[1],
                        phrase=entity_mention['text'],
                    )
                    if start_idx !=-1:
                        entity_mention['start'] = start_idx
                        entity_mention['end'] = end_idx
                        data['golden-entity-mentions'].append(entity_mention)
                    else:
                        print('##error: not found entity in sentence: ',entity_mention['text'], '--', entity_mention['position'])
                        print('sent: ',data['sentence'],'--',item['position'])

                    del entity_mention['position']


                # add to list data for conll file
                map_entityid2tag = dict()
                for it, entity in enumerate(data['golden-entity-mentions']):

                    map_entityid2tag.update({entity['entity-id'] : 'T'+str(id_doc)+ '_'+str(id_tag)})
                    # del data['golden-entity-mentions'][it]['entity-id']
                    pos = 0
                    type = entity['entity-type'].split(':')

                    for id in range(entity['start'], entity['end']):
                        try:
                            sentence_withNE[id][3] = 'T'+str(id_doc)+ '_'+str(id_tag)
                            sentence_withNE_short_ori[id][3] = 'T'+str(id_doc)+ '_'+str(id_tag)
                            sentence_withNE_short[id][3] = 'T'+str(id_doc)+ '_'+str(id_tag)

                            if(pos ==0):
                                sentence_withNE[id][2] = 'B-' + entity['entity-type']
                                sentence_withNE_short_ori[id][2] = 'B-' + type[0]

                                if len(type)>1:
                                    sentence_withNE_short[id][2] = 'B-' + type[1]
                                else:
                                    sentence_withNE_short[id][2] = 'B-' + type[0]


                            else:
                                sentence_withNE[id][2] = 'I-' + entity['entity-type']
                                sentence_withNE_short_ori[id][2] = 'I-' + type[0]

                                if len(type)>1:
                                    sentence_withNE_short[id][2] = 'I-' + type[1]
                                else:
                                    sentence_withNE_short[id][2] = 'I-' + type[0]

                        except Exception as e:
                            print(e)
                            print('--> check entity error:')
                            print(sentence_withNE)
                            print(entity['entity-type'])
                            print(entity['text'])

                        pos +=1

                    id_tag +=1


                for event_mention in item['golden-event-mentions']:

                    event_mention = copy.deepcopy(event_mention)
                    position = event_mention['trigger']['position']

                    start_idx, end_idx = find_token_index(
                        tokens=tokens,
                        start_pos=position[0] - sent_start_pos,
                        end_pos=position[1] - sent_start_pos + 1,
                        phrase=event_mention['trigger']['text'],
                    )
                    if start_idx != -1:
                        event_mention['trigger']['start'] = start_idx
                        event_mention['trigger']['end'] = end_idx

                        arguments = []
                        for argument in event_mention['arguments']:
                            position = argument['position']
                            start_idx, end_idx = find_token_index(
                                tokens=tokens,
                                start_pos=position[0] - sent_start_pos,
                                end_pos=position[1] - sent_start_pos + 1,
                                phrase=argument['text'],
                            )
                            argument['start'] = start_idx
                            argument['end'] = end_idx
                            del argument['position']

                            arguments.append(argument)

                        event_mention['arguments'] = arguments
                        data['golden-event-mentions'].append(event_mention)
                    else:
                        print('##error: not found event in sentence: ',event_mention['trigger']['text'], '--', position)
                        print('trigger: ',event_mention['trigger']['text'],'--', event_mention['trigger']['position'])
                        print('sent: ',tokens, '--', data['sentence'],'--',item['position'])

                    del event_mention['trigger']['position']

                # create data to built conll format data
                for ie, event in enumerate(data['golden-event-mentions']):

                    pos = 0
                    type = event['event_type'].split(':')
                    for id in range(event['trigger']['start'], event['trigger']['end']):
                        sentence_withNE[id][3] = 'E' + str(id_doc) + '_' + str(id_event)
                        sentence_withNE_short_ori[id][3] = 'E' + str(id_doc) + '_' + str(id_event)
                        sentence_withNE_short[id][3] = 'E' + str(id_doc) + '_' + str(id_event)
                        try:
                            if(pos ==0):
                                sentence_withNE[id][1] = 'B-' + event['event_type']
                                if len(type)>1:
                                    sentence_withNE_short_ori[id][1] = 'B-' + type[1]
                                    sentence_withNE_short[id][1] = 'B-' + type[1]

                                else:
                                    sentence_withNE_short_ori[id][1] = 'B-' + type[0]
                                    sentence_withNE_short[id][1] = 'B-' + type[0]

                            else:
                                sentence_withNE[id][1] = 'I-' + event['event_type']
                                if len(type)>1:
                                    sentence_withNE_short_ori[id][1] = 'I-' + type[1]
                                    sentence_withNE_short[id][1] = 'I-' + type[1]
                                else:
                                    sentence_withNE_short_ori[id][1] = 'I-' + type[0]
                                    sentence_withNE_short[id][1] = 'I-' + type[0]

                        except:
                            print('--> check event error:')
                            print(sentence_withNE)
                            print(event['event_type'])
                            print(event['trigger']['text'])

                        pos +=1

                        # add list arg_type:tag_entity

                        for ia, arg in enumerate(event['arguments']):
                            try:
                                sentence_withNE[id][4].append(arg['role'] + ':' + map_entityid2tag[arg['entity-id']])
                                sentence_withNE_short_ori[id][4].append(arg['role'] + ':' + map_entityid2tag[arg['entity-id']])
                                sentence_withNE_short[id][4].append(arg['role'] + ':' + map_entityid2tag[arg['entity-id']])
                                # del data['golden-event-mentions'][ie]['arguments'][ia]['entity-id']
                            except:
                                pass

                    id_event +=1

                document_conll_NE_full.append(sentence_withNE)
                document_conll_NE_short_ori.append(sentence_withNE_short_ori)
                document_conll_NE_short.append(sentence_withNE_short)
                document_json.append(data)

        split_name = file.split('/')
        if not os.path.isdir('conll_short_NE_ori/{}/{}'.format(data_type, split_name[-3])):
            os.makedirs('conll_short_NE_ori/{}/{}'.format(data_type, split_name[-3]), exist_ok=True)


        pathsave = 'conll_short_NE_ori/{}/{}/'.format(data_type, split_name[-3])
        # os.makedirs(pathsave, exist_ok=True)
        writeconll_EachFile(pathsave + split_name[-1] + '.txt', document_conll_NE_short_ori)

        if not os.path.isdir('conll_full/{}/{}'.format(data_type, split_name[-3])):
            os.makedirs('conll_full/{}/{}'.format(data_type, split_name[-3]))

        split_name = file.split('/')
        pathsave = 'conll_full/{}/{}/'.format(data_type, split_name[-3])
        # os.makedirs(pathsave, exist_ok=True)
        writeconll_EachFile(pathsave + split_name[-1] + '.txt', document_conll_NE_full)

        if not os.path.isdir('conll_short_NE/{}/{}'.format(data_type, split_name[-3])):
            os.makedirs('conll_short_NE/{}/{}'.format(data_type, split_name[-3]))

        split_name = file.split('/')
        pathsave = 'conll_short_NE/{}/{}/'.format(data_type, split_name[-3])
        # os.makedirs(pathsave, exist_ok=True)
        writeconll_EachFile(pathsave + split_name[-1] + '.txt', document_conll_NE_short)



        result.update({file : document_json})
        result_conll_1.update({'**Doc_{}**: '.format(id_doc) + file : document_conll_NE_full})
        result_conll_2.update({'**Doc_{}**: '.format(id_doc) + file : document_conll_NE_short_ori})
        result_conll_3.update({'**Doc_{}**: '.format(id_doc) + file : document_conll_NE_short})
        id_doc +=1

    print(set_deps)
    print('sent_count :', sent_count)
    print('event_count :', event_count)
    print('entity_count :', entity_count)
    print(value_tags)

    # with open('output3/{}.json'.format(data_type), 'w') as f:
    #     json.dump(result, f, indent=2)
    #
    # writealldoc2conll('output/{}_full.txt'.format(data_type), result_conll_1)
    # writealldoc2conll('output/{}_short_ori.txt'.format(data_type), result_conll_2)
    # writealldoc2conll('output/{}_short.txt'.format(data_type), result_conll_3)

    print(tags)

def writeconll_EachFile(path, data):

    with open(path, 'w', encoding='utf-8') as f:
        for sent in data:
            for word in sent:
                for tag in word[:-1]:
                    f.write(tag + '\t')
                for t, arg in enumerate(word[-1]):
                    f.write(arg + ' ')
                f.write('\n')

            f.write('\n')

def writealldoc2conll(path, data):

    with open(path, 'w', encoding='utf-8') as f:
        for doc_id in data:
            f.write(doc_id+'\n')
            for sent in data[doc_id]:
                for word in sent:
                    for tag in word[:-1]:
                        f.write(tag + '\t')

                    for arg in word[-1]:
                        f.write(arg+' ')
                    f.write('\n')

                f.write('\n')



path = '/home/thanhduc/data/event/ACE/package/ace_2005_td_v7/data/English/'
test_files, dev_files, train_files = get_data_paths(path)
with StanfordCoreNLP('/home/thanhduc/Downloads/stanford-corenlp-4.5.3', memory='8g', timeout=30000) as nlp:
    # import nltk
    # nltk.download('punkt')
    # sent = "Retired General Electric Co. Chairman Jack Welch is seeking work related documents of his estranged wife in his high stakes divorce case."
    # sent = "america warns it will seek more layoffs if it does file for chapter 11. number of companies are planning to cut their payrolls."
    # sent = "Another argument , which is better but still disturbing , is that , yes , this is an ethics violation , and maybe worse , but it would only hurt the USCF to talk about it , and that only troublemakers like Sam Sloan , Larry Parr , and , I suppose , me , would talk about it , since doing so will obstruct the federation 's plans , cause us to pay legal expenses , run the risk of our being stuck without any office space at all , cause people not to loan us money , and so forth ."
    # # sent = "there is more outrage about perks for executives, both from angry employees and from shareholders as well."
    sent= "Or , if you want to do things the SEC 's way , you could 1 ) Hire a bunch of lawyers with the company 's ( shareholders ' ) money , 2 ) Hire a legion of PR firms to explain away that frivolous spending , 3 ) Hire a new accountant to magically turn that spending into an investment amortizable over twenty years , and 4 ) Settle out of court by having the execs give the SEC some pittance ( for which they 'll likely be compensated by the company ) and a statement that \" We neither admit nor deny that we did what you claim , but we 'll never do it again .\""
    nlp_text = nlp.annotate(sent, properties={'annotators': 'tokenize, depparse'})
    nlp_res = json.loads(nlp_text)
    print(nlp_res)

    if len(nlp_res['sentences']) > 1:
        start_next_sent = nlp_res['sentences'][0]['tokens'][-1]['index'] if len(nlp_res['sentences'][0]['tokens']) > 0 else 0
        curr_id = 0
        tokens = nlp_res['sentences'][0]['tokens']
        deps = nlp_res['sentences'][0]['enhancedPlusPlusDependencies']
        for sentence in nlp_res['sentences'][1:]:
            for token in sentence['tokens']:
                curr_id = token['index']
                token['index'] = token['index'] + start_next_sent
                tokens.append(token)
            for dep in sentence['enhancedPlusPlusDependencies']:
                if dep['dep'] != "ROOT":
                    dep['governor'] += start_next_sent

                dep['dependent'] += start_next_sent
                deps.append(dep)

            start_next_sent += curr_id

    rows, cols = [], []
    for sent in nlp_res['sentences'][:1]:
        for dep in sent['basicDependencies']:
            if dep['dep'] == "ROOT": continue
            rows.append(dep['governor'] - 1)
            cols.append(dep['dependent'] - 1)
            cols.append(dep['governor'] - 1)
            rows.append(dep['dependent'] - 1)

    print([rows, cols])
    #
    # print(nlp_res['sentences'][0])

    # test_files = ['C:/Users/dell/Desktop/package/ace_2005_td_v7/data/English/un/timex2norm/misc.taxes_20050218.1250']
    # train_files = ['C:/Users/dell/Desktop/package/ace_2005_td_v7/data/English/un/timex2norm/rec.games.chess.politics_20041217.2111']

    preprocessing('dev', dev_files)
    # preprocessing('test', test_files)
    # preprocessing('train', train_files)

