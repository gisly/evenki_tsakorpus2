#!/usr/bin/python
# -*- coding: utf-8 -*
import re
import shutil
import nltk
from nltk.collocations import *
import numpy as np
from scipy import stats
import pandas as pd
__author__ = "gisly"


from lxml import etree
import os
import codecs


def create_parent_tier_from_annotation_concatenation(filename, new_filename,
                                                     parent_tier, tier_to_concatenate,
                                                     new_tier_name, end_delimiter = '.', tier_number=''):
    srcTree = etree.parse(filename)
    parent_tier_element = srcTree.xpath('/ANNOTATION_DOCUMENT/TIER[@TIER_ID="' +
                                                parent_tier + tier_number + '"]')[0]
    tier_to_concatenate_element = srcTree.xpath('/ANNOTATION_DOCUMENT/TIER[@TIER_ID="' +
                                                tier_to_concatenate + tier_number+ '"]')[0]
    new_tier_element = etree.SubElement(srcTree.getroot(), 'TIER', DEFAULT_LOCALE = 'ru',
                                       LINGUISTIC_TYPE_REF = parent_tier_element.attrib['LINGUISTIC_TYPE_REF'],
                                       TIER_ID = new_tier_name + tier_number)

    for alignable_annotation in srcTree.xpath('/ANNOTATION_DOCUMENT/TIER[@TIER_ID="' +
                                                   parent_tier + tier_number + '"]/ANNOTATION/'
                                              'ALIGNABLE_ANNOTATION'):
        new_tier_element_annotation = etree.SubElement(new_tier_element, 'ANNOTATION')
        new_tier_element_alignable_annotation = \
            etree.SubElement(new_tier_element_annotation, 'ALIGNABLE_ANNOTATION',
            ANNOTATION_ID = new_tier_name  + tier_number + "_" + alignable_annotation.attrib['ANNOTATION_ID'],
            TIME_SLOT_REF1 = alignable_annotation.attrib['TIME_SLOT_REF1'],
            TIME_SLOT_REF2 = alignable_annotation.attrib['TIME_SLOT_REF2'])
        new_tier_annotation_value = etree.SubElement(new_tier_element_alignable_annotation,
                                                     'ANNOTATION_VALUE')
        new_tier_annotation_value.text = \
            get_concatenation(tier_to_concatenate_element,
                              alignable_annotation.attrib['ANNOTATION_ID']) + end_delimiter

    all_tiers = srcTree.xpath('/ANNOTATION_DOCUMENT/TIER')
    for tier in all_tiers:
        if tier.attrib.get('PARENT_REF') == parent_tier + tier_number:
            tier.attrib['PARENT_REF'] = new_tier_name + tier_number
            for annotation in tier.xpath('ANNOTATION/REF_ANNOTATION'):
                annotation.attrib['ANNOTATION_REF'] = new_tier_name  + tier_number + "_" + annotation.attrib['ANNOTATION_REF']


    srcTree.write(new_filename)


def create_child_tier_from_annotation_concatenation(filename, new_filename,
                                                    parent_tier, tier_to_concatenate, new_tier_name,
                                                    tier_number):
    srcTree = etree.parse(filename)
    tier_to_concatenate_element = srcTree.xpath('/ANNOTATION_DOCUMENT/TIER[@TIER_ID="' +
                                                tier_to_concatenate + tier_number + '"]')[0]
    new_tier_element = etree.SubElement(srcTree.getroot(), 'TIER', DEFAULT_LOCALE = 'ru',
                                       LINGUISTIC_TYPE_REF = tier_to_concatenate_element.attrib['LINGUISTIC_TYPE_REF'],
                                       TIER_ID = new_tier_name + tier_number)

    for parent_annotation in srcTree.xpath('/ANNOTATION_DOCUMENT/TIER[@TIER_ID="' +
                                                   parent_tier + tier_number + '"]/ANNOTATION/'
                                              'REF_ANNOTATION'):
        new_tier_element_annotation = etree.SubElement(new_tier_element, 'ANNOTATION')
        new_tier_element_ref_annotation = \
            etree.SubElement(new_tier_element_annotation, 'REF_ANNOTATION',
            ANNOTATION_ID = new_tier_name  + tier_number  + '_' + parent_annotation.attrib['ANNOTATION_ID'],
            ANNOTATION_REF = parent_annotation.attrib['ANNOTATION_ID'])


        new_tier_annotation_value = etree.SubElement(new_tier_element_ref_annotation,
                                                     'ANNOTATION_VALUE')
        new_tier_annotation_value.text = get_concatenation(tier_to_concatenate_element,
                                                           parent_annotation.attrib['ANNOTATION_ID'],
                                                           '')
    srcTree.write(new_filename)


def create_child_gloss_tier_from_annotation_concatenation(filename,
                                                          new_filename,
                                                          parent_tier,
                                                          tier_to_concatenate_parent,
                                                          tier_to_concatenate, new_tier_name, tier_number):
    srcTree = etree.parse(filename)
    tier_to_concatenate_element = srcTree.xpath('/ANNOTATION_DOCUMENT/TIER[@TIER_ID="' +
                                                tier_to_concatenate + tier_number + '"]')[0]
    tier_to_concatenate_parent_element = srcTree.xpath('/ANNOTATION_DOCUMENT/TIER[@TIER_ID="' +
                                                       tier_to_concatenate_parent + tier_number + '"]')[0]
    new_tier_element = etree.SubElement(srcTree.getroot(), 'TIER', DEFAULT_LOCALE = 'ru',
                                       LINGUISTIC_TYPE_REF = tier_to_concatenate_element.attrib['LINGUISTIC_TYPE_REF'],
                                       TIER_ID = new_tier_name + tier_number)

    for parent_annotation in srcTree.xpath('/ANNOTATION_DOCUMENT/TIER[@TIER_ID="' +
                                                   parent_tier  + tier_number+ '"]/ANNOTATION/'
                                              'REF_ANNOTATION'):
        new_tier_element_annotation = etree.SubElement(new_tier_element, 'ANNOTATION')
        new_tier_element_ref_annotation = \
            etree.SubElement(new_tier_element_annotation, 'REF_ANNOTATION',
            ANNOTATION_ID = new_tier_name + tier_number + '_' + parent_annotation.attrib['ANNOTATION_ID'],
            ANNOTATION_REF = parent_annotation.attrib['ANNOTATION_ID'])


        new_tier_annotation_value = etree.SubElement(new_tier_element_ref_annotation,
                                                     'ANNOTATION_VALUE')
        new_tier_annotation_value.text = get_child_concatenation(tier_to_concatenate_parent_element,
                                                                 tier_to_concatenate_element,
                                                           parent_annotation.attrib['ANNOTATION_ID'],
                                                           '')
    srcTree.write(new_filename)

def convert_plain_file(filename, new_filename, word_tier_name,
                       morphemes_tier_name, glosses_tier_name, parent_name):
    srcTree = etree.parse(filename)
    morphemes_tier_element = srcTree.xpath('/ANNOTATION_DOCUMENT/TIER[@TIER_ID="' +
                                        morphemes_tier_name + '"]')[0]
    glosses_tier_element = srcTree.xpath('/ANNOTATION_DOCUMENT/TIER[@TIER_ID="' +
                                         glosses_tier_name + '"]')[0]

    new_word_tier_element = etree.SubElement(srcTree.getroot(), 'TIER', DEFAULT_LOCALE='ru',
                                        LINGUISTIC_TYPE_REF=morphemes_tier_element.attrib['LINGUISTIC_TYPE_REF'],
                                        TIER_ID=word_tier_name,
                                        PARENT_REF=parent_name)
    new_morpheme_tier_element = etree.SubElement(srcTree.getroot(), 'TIER', DEFAULT_LOCALE='ru',
                                        LINGUISTIC_TYPE_REF=morphemes_tier_element.attrib['LINGUISTIC_TYPE_REF'],
                                        TIER_ID=morphemes_tier_name + "Concat",
                                        PARENT_REF=word_tier_name)
    new_gl_tier_element = etree.SubElement(srcTree.getroot(), 'TIER', DEFAULT_LOCALE='ru',
                                                 LINGUISTIC_TYPE_REF=morphemes_tier_element.attrib['LINGUISTIC_TYPE_REF'],
                                                 TIER_ID=glosses_tier_name + "Concat",
                                                 PARENT_REF=word_tier_name)
    for parent_annotation in srcTree.xpath('/ANNOTATION_DOCUMENT/TIER[@TIER_ID="' +
                                                      parent_name + '"]/ANNOTATION/'
                                              'ALIGNABLE_ANNOTATION'):
        annotation_id = parent_annotation.attrib['ANNOTATION_ID']
        morphemes = morphemes_tier_element.xpath('ANNOTATION/REF_ANNOTATION'
                                                              '[@ANNOTATION_REF="' +
                                                                      annotation_id + '"]/ANNOTATION_VALUE/text()')[0]
        words = morphemes.strip().split(" ")
        glosses = glosses_tier_element.xpath('ANNOTATION/REF_ANNOTATION'
                                              '[@ANNOTATION_REF="' +
                                              annotation_id + '"]/ANNOTATION_VALUE/text()')[0]
        glosses_parts = glosses.strip().split(" ")
        if len(glosses_parts) != len(words):

            raise Exception("len(glosses) != len(words)")


        previous_annotation_id = None
        for word_index, word in enumerate(words):
            new_tier_element_annotation = etree.SubElement(new_word_tier_element, 'ANNOTATION')
            word_annotation_id = word_tier_name + '_' + parent_annotation.attrib['ANNOTATION_ID'] \
                                 + "_" + str(word_index)
            new_tier_element_ref_annotation = \
                etree.SubElement(new_tier_element_annotation, 'REF_ANNOTATION',
                                 ANNOTATION_ID=word_annotation_id,
                                 ANNOTATION_REF=parent_annotation.attrib['ANNOTATION_ID'])

            if parent_annotation.attrib['ANNOTATION_ID'] == 'sentFon_a310926':
                print('a')

            if previous_annotation_id:
                new_tier_element_ref_annotation.attrib['PREVIOUS_ANNOTATION'] = previous_annotation_id
            new_tier_annotation_value = etree.SubElement(new_tier_element_ref_annotation,
                                                         'ANNOTATION_VALUE')
            word_cleared = re.sub('[\-\.\=]', '', word)
            new_tier_annotation_value.text = word_cleared
            previous_annotation_id = word_annotation_id

            new_morpheme_element_annotation = etree.SubElement(new_morpheme_tier_element, 'ANNOTATION')
            morpheme_annotation_id = morphemes_tier_name + '_' + parent_annotation.attrib['ANNOTATION_ID'] \
                                 + "_" + str(word_index)
            new_morpheme_element_ref_annotation = \
                etree.SubElement(new_morpheme_element_annotation, 'REF_ANNOTATION',
                                 ANNOTATION_ID=morpheme_annotation_id,
                                 ANNOTATION_REF=word_annotation_id)

            new_morpheme_element_ref_annotation_value = etree.SubElement(new_morpheme_element_ref_annotation,
                                                         'ANNOTATION_VALUE')
            new_morpheme_element_ref_annotation_value.text = word

            new_gloss_element_annotation = etree.SubElement(new_gl_tier_element, 'ANNOTATION')
            gloss_annotation_id = glosses_tier_name + '_' + parent_annotation.attrib['ANNOTATION_ID'] \
                                     + "_" + str(word_index)
            new_gloss_element_ref_annotation = \
                etree.SubElement(new_gloss_element_annotation, 'REF_ANNOTATION',
                                 ANNOTATION_ID=gloss_annotation_id,
                                 ANNOTATION_REF=word_annotation_id)

            new_gloss_element_ref_annotation_value = etree.SubElement(new_gloss_element_ref_annotation,
                                                                         'ANNOTATION_VALUE')
            new_gloss_element_ref_annotation_value.text = glosses_parts[word_index]


    srcTree.write(new_filename)


def copy_main_tier_to_child(filename, new_filename, main_tier, tier_model, new_tier, new_tier_parent, tier_number):
    srcTree = etree.parse(filename)
    main_tier_element = srcTree.xpath('/ANNOTATION_DOCUMENT/TIER[@TIER_ID="' +
                                      main_tier  + tier_number + '"]')[0]
    tier_model_element = srcTree.xpath('/ANNOTATION_DOCUMENT/TIER[@TIER_ID="' +
                                      tier_model + tier_number + '"]')[0]

    new_tier_element = etree.SubElement(srcTree.getroot(), 'TIER', DEFAULT_LOCALE='ru',
                                        LINGUISTIC_TYPE_REF=tier_model_element.attrib['LINGUISTIC_TYPE_REF'],
                                        TIER_ID=new_tier + tier_number,
                                        PARENT_REF=new_tier_parent + tier_number)
    for alignable_annotation in main_tier_element.xpath('ANNOTATION/'
                                              'ALIGNABLE_ANNOTATION'):
        new_tier_element_annotation = etree.SubElement(new_tier_element, 'ANNOTATION')
        new_tier_element_ref_annotation = \
            etree.SubElement(new_tier_element_annotation, 'REF_ANNOTATION',
            ANNOTATION_REF = new_tier_parent + tier_number + '_' + alignable_annotation.attrib['ANNOTATION_ID'],
            ANNOTATION_ID = new_tier  + tier_number + '_' + alignable_annotation.attrib['ANNOTATION_ID'])
        new_tier_annotation_value = etree.SubElement(new_tier_element_ref_annotation,
                                                     'ANNOTATION_VALUE')
        new_tier_annotation_value.text = \
            alignable_annotation.getchildren()[0].text

    srcTree.write(new_filename)

def get_child_concatenation(tier_to_concatenate_parent_element, tier_to_concatenate_element, annotation_id,
                            delimiter=' '):
    concatenated_values = ''
    for annotation in tier_to_concatenate_parent_element.xpath('ANNOTATION/REF_ANNOTATION'
                                                              '[@ANNOTATION_REF="' +
                                                                      annotation_id + '"]'):
        curAnnotationValue = annotation.xpath('ANNOTATION_VALUE/text()')[0]

        """concatenated_values += '' + get_concatenation(tier_to_concatenate_element, annotation.attrib['ANNOTATION_ID'],
                                                 '-')"""
        if curAnnotationValue.startswith('-'):
            delim = '-'
        elif curAnnotationValue.startswith('='):
            delim = '-'
        else:
            delim = ' '
        concatenated_values += delim + get_concatenation(tier_to_concatenate_element, annotation.attrib['ANNOTATION_ID'],
                                                         '')
    return re.sub('\-+', '-', concatenated_values.strip('-').strip())



def get_concatenation(tier_to_concatenate_element, annotation_id, delimiter=' '):
    concatenated_values = ''
    for annotation_value in tier_to_concatenate_element.xpath('ANNOTATION/REF_ANNOTATION'
                                              '[@ANNOTATION_REF="' +
                                                annotation_id + '"]/ANNOTATION_VALUE/text()'):
        concatenated_values += delimiter + annotation_value
    return concatenated_values.strip()

def prepare_file(filename, output_folder, language_tier_name, tier_number_list):
    new_filename = os.path.join(output_folder, os.path.basename(filename))
    for tier_number in tier_number_list:
        create_parent_tier_from_annotation_concatenation(filename, new_filename, language_tier_name, "fonWord",
                                                         "sentFon", '', tier_number)
        create_child_tier_from_annotation_concatenation(new_filename, new_filename,
                                                                       "fonWord", "fon", "fonConcat", tier_number)
        create_child_gloss_tier_from_annotation_concatenation(new_filename,new_filename,
                                                                             "fonWord", "fon", "gl", "glConcat", tier_number)
        copy_main_tier_to_child(new_filename, new_filename,
                                               language_tier_name, "rus", language_tier_name + "Cyr", "sentFon", tier_number)
    return new_filename

def preprocess_folder(folder, output_folder, meta_folder, language_tier_name = "ev", tier_list=set()):
    with codecs.open(os.path.join(meta_folder, 'meta.csv'), 'a', 'utf-8') as fout:
        #fout.write('filename\r\n')
        for base_filename in os.listdir(folder):
            filename = os.path.join(folder, base_filename)
            if os.path.isfile(filename) and filename.lower().endswith('.eaf'):
                print('starting to process: %s' % filename)
                try:
                    new_filename = prepare_file(filename, output_folder, language_tier_name, tier_list)
                    #fout.write(os.path.splitext(os.path.basename(new_filename))[0] + '\n')
                    print('processed: %s'  % filename)
                except Exception as e:
                    print(e)
                    print('error occurred when processing: %s' % filename)



def copy_media_for_file(filename, folder_media):
    media_file_uri = get_media_file_uri(filename)
    if not media_file_uri:
        print('No media for %s' % filename)
        return
    if not os.path.exists(media_file_uri):
        print('File does not exist for %s: %s' % (media_file_uri, filename))
        return
    if media_file_uri.endswith('.avi'):
        print('AVI file for %s: %s' % (media_file_uri, filename))
        return
    base_filename = os.path.basename(media_file_uri)
    target_filename = os.path.join(folder_media, base_filename)
    shutil.copy(media_file_uri, target_filename)

def get_media_file_uri(filename):
    srcTree = etree.parse(filename)
    main_media_elements = srcTree.xpath('/ANNOTATION_DOCUMENT/HEADER/MEDIA_DESCRIPTOR'
                                        '[@MIME_TYPE="audio/x-wav"]')
    if not main_media_elements:
        main_media_elements = srcTree.xpath('/ANNOTATION_DOCUMENT/HEADER/MEDIA_DESCRIPTOR')
    if not main_media_elements:
        return None
    return main_media_elements[0].attrib['MEDIA_URL'].split('file:///')[-1]

def copy_media(folder_eaf, folder_media):
    for filename in os.listdir(folder_eaf):
        full_eaf_filename = os.path.join(folder_eaf, filename)
        copy_media_for_file(full_eaf_filename, folder_media)
        print('Moved file for %s' % full_eaf_filename)


def process_glosses(folder_eaf):
    gloss_set = set()
    for filename in os.listdir(folder_eaf):
        full_eaf_filename = os.path.join(folder_eaf, filename)
        if os.path.isfile(full_eaf_filename) and filename.endswith('.eaf'):
            gloss_set = gloss_set.union(get_glosses_from_file(full_eaf_filename))
    sorted_gloss_list = sorted(list(gloss_set))
    for gloss in sorted_gloss_list:
        print(gloss)

def get_glosses_from_file(filename):
    gloss_set = set()
    srcTree = etree.parse(filename)
    gloss_tier_element = srcTree.xpath('/ANNOTATION_DOCUMENT/TIER[@TIER_ID="gl"]')[0]
    for ref_annotation in gloss_tier_element.xpath('ANNOTATION/'
                                              'REF_ANNOTATION/ANNOTATION_VALUE'):
        gloss_text = normalize_gloss(ref_annotation.text)
        if is_grammar_gloss(gloss_text):
            gloss_set.add(gloss_text.upper())
    return gloss_set

def normalize_gloss(gloss):
    if '.SLIP' in gloss:
        return 'SLIP'
    gloss = gloss.strip().strip('-').replace('(?)', '')
    for bad_char in '{*}[]?':
        gloss = gloss.replace(bad_char, '')
    return gloss

def is_grammar_gloss(gloss):
    if gloss == '':
        return False
    gloss_removed_everything = re.sub('[a-z0-9-.]', '', gloss.lower())
    return len(gloss_removed_everything) == 0



def export_all_sentences_from_file(filename, tier_name, child_name, grandchild_name):
    sentences = []
    words = []
    stems = []
    srcTree = etree.parse(filename)
    parent_tier_elements = srcTree.xpath('/ANNOTATION_DOCUMENT/TIER[@TIER_ID="' +
                                        tier_name  + '"]')
    tier_numbers = ['']
    if not parent_tier_elements:
        tier_numbers = ['1', '2']

    for tier_number in tier_numbers:
        for alignable_annotation in srcTree.xpath('/ANNOTATION_DOCUMENT/TIER[@TIER_ID="' +
                                                  tier_name + tier_number + '"]/ANNOTATION/'
                                                                              'ALIGNABLE_ANNOTATION'):
            parent_id = alignable_annotation.attrib['ANNOTATION_ID']
            sentence = ''
            for word_annotation_ref in srcTree.xpath('/ANNOTATION_DOCUMENT/TIER[@TIER_ID="' +
                                                      child_name + tier_number + '"]/ANNOTATION/'
                                                             'REF_ANNOTATION[@ANNOTATION_REF="' + parent_id + '"]'):

                child_id = word_annotation_ref.attrib['ANNOTATION_ID']
                word_text = word_annotation_ref.find('ANNOTATION_VALUE').text
                words.append(word_text)
                for morpheme_annotation_ref in srcTree.xpath('/ANNOTATION_DOCUMENT/TIER[@TIER_ID="' +
                                                    grandchild_name + tier_number + '"]/ANNOTATION/'
                                                                               'REF_ANNOTATION[@ANNOTATION_REF="' + child_id + '"]/ANNOTATION_VALUE'):
                    morpheme_text = morpheme_annotation_ref.text
                    if not morpheme_text.startswith('-') and not morpheme_text.startswith('='):
                        sentence += ' ' + morpheme_text
                        stems.append(morpheme_text)

            sentences.append(sentence.strip())
    return words, stems, sentences

def export_all_sentences(folder_name, tier_name, child_name, grandchild_name):
    sentences = []
    words = []
    stems = []
    for filename in os.listdir(folder_name):
        if not filename.endswith('.eaf'):
            continue
        full_filename = os.path.join(folder_name, filename)
        words_file, stems_file, sentences_file = export_all_sentences_from_file(full_filename, tier_name, child_name, grandchild_name)
        sentences += sentences_file
        words += words_file
        stems += stems_file
    output_filename = os.path.join(folder_name, 'out.txt')
    with open(output_filename, 'w', encoding='utf-8', newline='') as fout:
        for sentence in sentences:
            fout.write(sentence.strip() + '\n')
    return words, stems

def count_words_in_file(filename, tier_name, childtier_name=None, words=None):
    word_count = 0
    total_word_count = 0
    srcTree = etree.parse(filename)
    parent_tier_elements = srcTree.xpath('/ANNOTATION_DOCUMENT/TIER[@TIER_ID="' +
                                         tier_name + '"]')
    tier_numbers = ['']
    if not parent_tier_elements:
        tier_numbers = ['1', '2']

    for tier_number in tier_numbers:
        total_word_count += len(srcTree.xpath('/ANNOTATION_DOCUMENT/TIER[@TIER_ID="' +
                                                             tier_name + tier_number + '"]/ANNOTATION/REF_ANNOTATION/ANNOTATION_VALUE'))
        if words is None:
            word_count = len(srcTree.xpath('/ANNOTATION_DOCUMENT/TIER[@TIER_ID="' +
                                                             tier_name + tier_number + '"]/ANNOTATION/REF_ANNOTATION/ANNOTATION_VALUE'))
        else:
            for word_annotation_ref in srcTree.xpath('/ANNOTATION_DOCUMENT/TIER[@TIER_ID="' +
                                            tier_name + tier_number + '"]/ANNOTATION/REF_ANNOTATION'):
                child_id = word_annotation_ref.attrib['ANNOTATION_ID']
                for morpheme_annotation_ref in srcTree.xpath('/ANNOTATION_DOCUMENT/TIER[@TIER_ID="' +
                                                             childtier_name + tier_number + '"]/ANNOTATION/'
                                                                               'REF_ANNOTATION[@ANNOTATION_REF="' + child_id + '"]/ANNOTATION_VALUE'):
                    morpheme_text = morpheme_annotation_ref.text
                    if not morpheme_text.startswith('-') and not morpheme_text.startswith('=') and morpheme_text in words:
                        word_count += 1


    return word_count, total_word_count


def get_text_group(meta_filename, meta_number):
    texts_groups = dict()
    with open(meta_filename, 'r', encoding='utf-8') as fin:
        for line in fin:
            line_parts = line.strip().split('\t')
            texts_groups[line_parts[0]] = line_parts[meta_number]
    return texts_groups

def count_words_by(folder_name, meta_filename, meta_number):
    groups_count = dict()
    texts_groups = get_text_group(meta_filename, meta_number)
    for filename in os.listdir(folder_name):
        if not filename.endswith('.eaf'):
            continue
        full_filename = os.path.join(folder_name, filename)
        group = texts_groups[filename]
        word_count, total_word_count = count_words_in_file(full_filename, 'fonWord')
        if group in texts_groups:
            groups_count[group] += word_count
        else:
            groups_count[group] = word_count
    groups_sorted = sorted(list(groups_count.keys()))
    for group_sorted in groups_sorted:
        print(group_sorted + '\t' + str(groups_count[group_sorted]))


def count_words_by_settlements(folder_name, meta_filename):
    count_words_by(folder_name, meta_filename, 3)


def count_words_by_persons(folder_name, meta_filename):
    count_words_by(folder_name, meta_filename, 1)


def split_and_count_word(folder_name, meta_filename, word_list):
    texts_groups = get_text_group(meta_filename, 3)
    person_name_text_groups = dict()
    person_name_group_texts = dict()
    person_name_group_texts[0] = 0
    person_name_group_texts[1] = 0
    for text, group in texts_groups.items():
        place = group.split(' ')[0]
        print(place)
        """if place in ['Чиринда', 'Эконда', 'Тутончаны', 'Ербогачён', 'Хантайское',
                     'Советская', 'Большое', 'Озеро', 'Кислокан', 'Юкта', 'Виви', 'Тура', '',
                     'Учами', 'Потапово']:"""
        if place in ['Чиринда']:
            person_name_text_groups[text] = 0
            person_name_group_texts[0] += 1
        else:
            person_name_text_groups[text] = 1
            person_name_group_texts[1] += 1
    groups_word_count = dict()
    for filename in os.listdir(folder_name):
        if not filename.endswith('.eaf'):
            continue
        full_filename = os.path.join(folder_name, filename)
        group = person_name_text_groups[filename]
        word_count, total_words = count_words_in_file(full_filename, 'fonWord', childtier_name='fon', words=word_list)
        freq = word_count / float(total_words)
        if freq > 0 and group > 0:
            print(filename)
        if group in groups_word_count:
            groups_word_count[group].append(freq)
        else:
            groups_word_count[group] = [freq]
    return groups_word_count[0], groups_word_count[1]

def check_normality(data):
    test_stat_normality, p_value_normality=stats.shapiro(data)
    print("p value:%.4f" % p_value_normality)
    if p_value_normality <0.05:
        print("Reject null hypothesis >> The data is not normally distributed")
    else:
        print("Fail to reject null hypothesis >> The data is normally distributed")

def main():
    """preprocess_folder("D://CompLing/CorpusUtils/tsakonian_corpus_platform/corpus/evenki//test//",
                      "D://CompLing/CorpusUtils/tsakonian_corpus_platform/corpus/evenki/eaf",
                      "D://CompLing/CorpusUtils/tsakonian_corpus_platform/corpus/evenki",
                      "ev",
                      ['']
                      )"""

    """all_words, all_stems = export_all_sentences("D://CompLing/CorpusUtils/tsakonian_corpus_platform/corpus/evenki/eaf", "sentFon",
                         "fonWord", "fon")"""

    """count_words_by_persons("D://CompLing/CorpusUtils/tsakorpus/corpus/evenki/eaf",
                               "D://CompLing/CorpusUtils/tsakorpus/corpus/evenki/meta.csv")"""
    """filename = 'D://Evenki/EvenkiLiterature/pushkin_dubrovskiy/dubrovskiy_evenki_book.txt'
    sentences_book = []
    text = ''
    with open(filename, 'r', encoding='utf-8') as fin:
        for line in fin:
            text += line.strip()
    sentences_book = re.split('[\.\!\?]', text)
    filename_out = filename + '_out.txt'
    with open(filename_out, 'w', encoding='utf-8', newline='') as fout:
        for sentence_book in sentences_book:
            sentence_book = sentence_book.strip()
            sentence_book = sentence_book.replace('- ', '')
            sentence_book = sentence_book.replace('„', '"')
            sentence_book = sentence_book.replace('“', '"')
            if sentence_book != '':
                fout.write(sentence_book + '\n')"""

    """
    bigram_measures = nltk.collocations.BigramAssocMeasures()
    trigram_measures = nltk.collocations.TrigramAssocMeasures()
    fourgram_measures = nltk.collocations.QuadgramAssocMeasures()

    finder = TrigramCollocationFinder.from_words(all_stems)
    finder.apply_freq_filter(3)
    tuples = finder.nbest(trigram_measures.pmi, 10)
    for tuple in tuples:
        print(' '.join(tuple))"""
    group1, group2 = split_and_count_word("D://CompLing/CorpusUtils/tsakorpus/corpus/evenki/eaf",
                           "D://CompLing/CorpusUtils/tsakorpus/corpus/evenki/meta.csv",
                         ["oldo", "huru"])

    group1 = np.array(group1)
    group2 = np.array(group2)
    print(group1, group2)
    check_normality(group1)
    check_normality(group2)

if __name__ == '__main__':
    main()
"""create_parent_tier_from_annotation_concatenation(,
                                          "ev", "fonWord", "evFon")

create_child_tier_from_annotation_concatenation("D://ForElan//ForSIL_CORPUS//"
                                          "evenki_corpus//eaf//2007_Chirinda_Eldogir_Valentina_FSk9_test.eaf_new.eaf",
                                          "fonWord", "fon", "fonConcat")

create_child_gloss_tier_from_annotation_concatenation("D://ForElan//ForSIL_CORPUS//"
                                          "evenki_corpus//eaf//2007_Chirinda_Eldogir_Valentina_FSk9_test.eaf_new.eaf_new.eaf",
                                          "fonWord", "fon", "gl", "glConcat")"""




#process_glosses("D://CompLing/CorpusUtils/tsakonian_corpus_platform/corpus/evenki/eaf")
"""
preprocess_folder("D://CompLing/CorpusUtils/tsakonian_corpus_platform/corpus/ket//test//",
                  "D://CompLing/CorpusUtils/tsakonian_corpus_platform/corpus/ket/eaf",
                  "D://CompLing/CorpusUtils/tsakonian_corpus_platform/corpus/ket",
                  "ket")"""
"""
create_child_gloss_tier_from_annotation_concatenation(
    "D://CompLing//CorpusUtils//tsakonian_corpus_platform//corpus//evenki//_old//"
                                                "2006_Sovrechka_Arkadieva_LR1.eaf_new.eaf",
"D://CompLing//CorpusUtils//tsakonian_corpus_platform//corpus//evenki//_old/"
                                                "2006_Sovrechka_Arkadieva_LR1.eaf_new2.eaf",
                                          "fonConcat", "fon", "gl", "glConcat")"""
"""

copy_media("D://CompLing/CorpusUtils/tsakonian_corpus_platform/corpus/evenki/test",
           "D://CompLing/CorpusUtils/tsakonian_corpus_platform/corpus/evenki/eaf/media")"""

