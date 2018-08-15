from alignment.sequence import Sequence
import alignment
alignment.sequence.GAP_ELEMENT = "ε"
from alignment.vocabulary import Vocabulary
from alignment.sequencealigner import SimpleScoring, GlobalSequenceAligner

from functools import reduce

import process_test_data as ptd

def get_adjusted_distance(l1, l2):

    scoring = SimpleScoring(2, -1)
    aligner = GlobalSequenceAligner(scoring, -2)

    a = Sequence(l1)
    b = Sequence(l2)

    # Create a vocabulary and encode the sequences.
    vocabulary = Vocabulary()
    source_seq = vocabulary.encodeSequence(a)
    target_seq = vocabulary.encodeSequence(b)


    _, alignments = aligner.align(source_seq, target_seq, backtrace=True)
    a = vocabulary.decodeSequenceAlignment(alignments[0]) # best result

    #print(a)

    d = 0 # distance
    length_reduction = max(l1.count(u"\u0364"), l2.count(u"\u0364"))

    #umlauts = {u"ä": "a", u"ö": "o", u"ü": "u"} # for example
    umlauts = {"a": u"ä", "o": u"ö", "u": u"ü"} # for example

    source_umlaut = ''
    target_umlaut = ''


    for source_sym, target_sym in zip(a.first, a.second):

        #print(source_sym, target_sym)

        if source_sym == target_sym:
            if source_umlaut: # previous source is umlaut non-error
                source_umlaut = False # reset
                d += 1 # one full error (mismatch)
            elif target_umlaut: # previous target is umlaut non-error
                target_umlaut = False # reset
                d += 1 # one full error (mismatch)

        else:
            if source_umlaut: # previous source is umlaut non-error
                if source_sym == u"\u0364" and\
                   target_sym == umlauts.get(source_umlaut): # diacritical combining e
                    d += 1.0 # umlaut error (match)
                elif source_sym == u"\u0364":
                    d += 1.0 # one error, because diacritical and other character (mismatch)
                else:
                    d += 2.0 # two full errors (mismatch)
                source_umlaut = '' # reset

            elif target_umlaut: # previous target is umlaut non-error
                if target_sym == u"\u0364" and\
                   source_sym == umlauts.get(target_umlaut): # diacritical combining e
                    d += 1.0 # umlaut error (match)
                elif target_sym == u"\u0364":
                    d += 1.0 # one error, because diacritical and other character (mismatch)
                else:
                    d += 2.0 # two full errors (mismatch)
                target_umlaut = '' # reset

            elif source_sym == alignment.sequence.GAP_ELEMENT and\
                target_sym in list(umlauts.keys()):
                target_umlaut = target_sym # umlaut non-error
                #print('set target_umlaut')

            elif target_sym == alignment.sequence.GAP_ELEMENT and\
                source_sym in list(umlauts.keys()):
                source_umlaut = source_sym # umlaut non-error
                #print('set source_umlaut')

            else:
                d += 1 # one full error

    if source_umlaut or target_umlaut: # previous umlaut error
        d += 1 # one full error



    #for source_sym, target_sym in zip(a.first, a.second):

    #    if source_sym == target_sym:
    #        if source_umlaut: # previous source is umlaut non-error
    #            source_umlaut = False # reset
    #            d += 1 # one full error (mismatch)
    #        elif target_umlaut: # previous target is umlaut non-error
    #            target_umlaut = False # reset
    #            d += 1 # one full error (mismatch)

    #    else:
    #        if source_umlaut: # previous source is umlaut non-error
    #            source_umlaut = False # reset
    #            if source_sym == alignment.sequence.GAP_ELEMENT and\
    #               target_sym == u"\u0364": # diacritical combining e
    #                d += 0.5 # umlaut error (match)
    #            else:
    #                d += 2.0 # two full errors (mismatch)
    #        elif target_umlaut: # previous target is umlaut non-error
    #            target_umlaut = False # reset
    #            if target_sym == alignment.sequence.GAP_ELEMENT and\
    #               source_sym == u"\u0364": # diacritical combining e
    #                d += 0.5 # umlaut error (match)
    #            else:
    #                d += 2.0 # two full errors (mismatch)
    #        elif umlauts.get(source_sym) == target_sym:
    #            source_umlaut = True # umlaut non-error
    #        elif umlauts.get(target_sym) == source_sym:
    #            target_umlaut = True # umlaut non-error
    #        else:
    #            d += 1 # one full error

    #if source_umlaut or target_umlaut: # previous umlaut error
    #    d += 1 # one full error


    #print(len(a), length_reduction)

    return d, len(a) - length_reduction # distance and adjusted length



def get_adjusted_cer(l1, l2):

    distance, length = get_adjusted_distance(l1, l2)

    length = length-16

    #print(length)

    return distance / length, length




def get_percent_identity(alignment):

    a1 = alignment[0]
    a2 = alignment[1]

    identity_count = 0;
    char_count = len(a1)

    for i, char in enumerate(a1):
        if a1[i] == a2[i]:
            identity_count += 1

    return identity_count / char_count



def align_lines(l1, l2):

    a = Sequence(l1)
    b = Sequence(l2)

    # Create a vocabulary and encode the sequences.
    v = Vocabulary()
    aEncoded = v.encodeSequence(a)
    bEncoded = v.encodeSequence(b)

    # Create a scoring and align the sequences using global aligner.
    scoring = SimpleScoring(2, -1)
    aligner = GlobalSequenceAligner(scoring, -2)
    score, encodeds = aligner.align(aEncoded, bEncoded, backtrace=True)

    for encoded in encodeds:
        alignment = v.decodeSequenceAlignment(encoded)
        alignment = list(alignment[8:-8])
        cer = 1 - get_percent_identity(alignment)

    return cer, len(alignment[0])


def main():

    #l1 = '########Mit unendlich ſuͤßem Sehnen########'
    #l2 = '########Mit unendlich ſüßem Sehnen########'
    #print(align_lines(l1, l2))
    #print(get_adjusted_distance(l1, l2))
    #print(get_adjusted_percent_identity(l1, l2))

    path = '../../dta19-reduced/testdata/'

    fraktur4_dict = ptd.create_dict(path, 'Fraktur4')
    gt_dict = ptd.create_dict(path, 'gt')
    corrected_dict = ptd.create_dict(path, 'Fraktur4_corrected')

    cer_list_fraktur4 = []
    cer_list_corrected = []

    for key in corrected_dict.keys():

        fraktur4_line = '########' + fraktur4_dict[key].strip() + '########'
        gt_line = '########' + gt_dict[key].strip() + '########'
        corrected_line = '########' +  corrected_dict[key].strip() + '########'

        print('Fraktur4:  ', fraktur4_line)
        print('GT:        ', gt_line)
        print('Corrected: ', corrected_line)

        #cer_fraktur4, fraktur4_len = align_lines(fraktur4_line, gt_line)
        cer_fraktur4, fraktur4_len = get_adjusted_cer(fraktur4_line, gt_line)
        #cer_corrected, corrected_len = align_lines(corrected_line, gt_line)
        cer_corrected, corrected_len = get_adjusted_cer(corrected_line, gt_line)

        print('CER Fraktur4:  ', cer_fraktur4)
        print('CER Corrected: ', cer_corrected)

        cer_list_fraktur4.append((cer_fraktur4, fraktur4_len))
        cer_list_corrected.append((cer_corrected, corrected_len))

    summed_chars_fraktur4 = reduce(lambda x,y: x + y[1], cer_list_fraktur4, 0)
    summed_weighted_cer_fraktur4 = reduce(lambda x,y: x + (y[0] * (y[1] / summed_chars_fraktur4)), cer_list_fraktur4, 0)

    print('Summed CER Fraktur4:  ', summed_weighted_cer_fraktur4)

    summed_chars_corrected = reduce(lambda x,y: x + y[1], cer_list_corrected, 0)
    summed_weighted_cer_corrected = reduce(lambda x,y: x + (y[0] * (y[1] / summed_chars_corrected)), cer_list_corrected, 0)

    print('Summed CER Corrected: ', summed_weighted_cer_corrected)




if __name__ == '__main__':
    main()