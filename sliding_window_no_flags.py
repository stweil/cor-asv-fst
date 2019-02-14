# TODO:
# - try processing with HFST optimized lookup?
# - refactoring (esp. recombine_windows()) and code cleaning

import hfst
import logging
from operator import itemgetter
import tempfile
import time

import helper
from extensions.composition import pyComposition
from sliding_window import lexicon_add_compounds, amend_lexicon_transducer


def _print_paths(paths):
    paths_lst = [(output_str.replace(hfst.EPSILON, ''), weight) \
                 for input_str, outputs in paths.items() \
                 for output_str, weight in outputs]
    paths_lst.sort(key=itemgetter(1))
    for p in paths_lst:
        logging.debug('{}\t{}'.format(*p))


def split_input_string(string):
    '''Split an input string around whitespaces.'''
    return string.split()


def create_window(tokens):
    '''
    Create a window for the given input tokens (supplied as a list of
    strings).
    '''
    return hfst.fst(' '.join(tokens))


def process_window_with_openfst(input_str, window_fst, model, rejection_weight=10):
    '''
    Compose a window input automaton with the model using OpenFST
    composition (lazy composition of error .o. lexicon).
    '''
    t1 = time.time()
    result_fst = None
    with tempfile.NamedTemporaryFile(prefix='cor-asv-fst-sw-input') as f:
        helper.save_transducer(
            f.name, window_fst, hfst_format=False, 
            type=hfst.ImplementationType.TROPICAL_OPENFST_TYPE)
        filename = model.correct_transducer_file(f.name)
    result_fst = helper.load_transducer(filename)
    t2 = time.time()
    logging.debug('Processing time: {}s'.format(t2-t1))
    return result_fst


def process_window_with_hfst(input_str, window_fst, model, n=10, rejection_weight=10):
    '''
    Compose a window input automaton with the model using HFST
    composition.
    '''
    t1 = time.time()
    for fst in model:
        window_fst.compose(fst)
    window_fst.minimize()
    window_fst.n_best(n)
    window_fst.output_project()
    if ' ' not in input_str:
        # allow also identity for windows of length 1
        # (with weight `rejection_weight`)
        window_fst.disjunct(hfst.fst((input_str, rejection_weight)))
    window_fst.minimize()
    t2 = time.time()
    logging.debug('states: {}'.format(window_fst.number_of_states()))
    logging.debug('Processing time: {}s'.format(t2-t1))
    return window_fst


def process_window(input_str, window_fst, model, rejection_weight=10):
    '''Compose a window input automaton with the model.'''
    if isinstance(model, pyComposition):
        return process_window_with_openfst(input_str, window_fst, model, rejection_weight)
    elif isinstance(model, tuple):
        return process_window_with_hfst(input_str, window_fst, model, rejection_weight)
    else:
        raise RuntimeError('Unknown model type: {}'.format(type(model)))


def recombine_windows(window_fsts):
    '''
    Recombine the window transducers into the transducer correcting the whole
    input string.
    '''

    t1 = time.time()

    # convert window fsts to basic transducers
    window_basic_fsts = { (i, j) : hfst.HfstBasicTransducer(window) \
                          for (i, j), window in window_fsts.items() }

    # determine the input string length and max. window size
    # (TODO without iterating!!!)
    num_tokens = max(i for (i, j) in window_fsts)+1
    max_window_size = max(j for (i, j) in window_fsts)

    result = hfst.HfstBasicTransducer()
    # add states:
    # 0 - the initial state
    # 1 - the final state
    result.add_state()
    assert result.states() == (0, 1)
    result.set_final_weight(1, 0.0)

    # create a dictionary translating the states of the window transducers to
    # the states of the resulting transducer
    state_dict = {}
    for (i, j), window in window_basic_fsts.items():
        for k in window.states():
            state_dict[(i, j, k)] = result.add_state()

    # add transitions leading to the first window of each size
    # (assuming that state 0 is initial in every HfstBasicTransducer!)
    for j in range(1, max_window_size+1):
        result.add_transition(
            0,
            hfst.HfstBasicTransition(
                state_dict[(0, j, 0)],
                hfst.EPSILON,
                hfst.EPSILON,
                0.0))

    for (i, j), window in window_basic_fsts.items():
        is_final_window = (i+j == num_tokens)
        for k in window.states():
            # add transitions inside the window FST
            for tr in window.transitions(k):
                result.add_transition(
                    state_dict[(i, j, k)],
                    hfst.HfstBasicTransition(
                        state_dict[(i, j, tr.get_target_state())],
                        tr.get_input_symbol(),
                        tr.get_output_symbol(),
                        tr.get_weight()))
            if window.is_final_state(k):
                if is_final_window:      # add a transition to the final state
                    result.add_transition(
                        state_dict[(i, j, k)],
                        hfst.HfstBasicTransition(
                            1,
                            hfst.EPSILON,
                            hfst.EPSILON,
                            window.get_final_weight(k)))
                else:                   # add transitions to next windows
                    new_i = i+j
                    for new_j in range(1, max_window_size+1):
                        if new_i+new_j <= num_tokens:
                            result.add_transition(
                                state_dict[(i, j, k)],
                                hfst.HfstBasicTransition(
                                    state_dict[(new_i, new_j, 0)],
                                    ' ',
                                    ' ',
                                    window.get_final_weight(k)))

    result = hfst.HfstTransducer(result)
    result.minimize()

    t2 = time.time()
    logging.debug('Recombining time: {}s'.format(t2-t1))

    return result


def process_string(string, model, max_window_size=2, rejection_weight=10):
    # create windows from the input string
    windows = {}
    tokens = split_input_string(string)
    for i in range(len(tokens)):
        for j in range(1, min(max_window_size+1, len(tokens)-i+1)):
            windows[(i,j)] = create_window(tokens[i:i+j])
    # compose each window with the model
    for (i, j) in windows:
        windows[(i,j)] = process_window(
            ' '.join(tokens[i:i+j]),
            windows[(i,j)], model,
            rejection_weight=rejection_weight)
        logging.debug('Processing window ({}, {})'.format(i, j))
        _print_paths(windows[(i,j)].extract_paths())
    # recombine the windows
    final_fst = recombine_windows(windows)
    return final_fst


#############################################################################
# Model-building functions (FIXME simplify, move the transducer-changing
# functionality to the lexicon training module)
#############################################################################


def single_token_to_window_acceptor(single_token_acceptor, space_tr):
    result = single_token_acceptor.copy()
    result.concatenate(space_tr)
    result.repeat_star()
    result.concatenate(single_token_acceptor)
    return result


def build_single_token_acceptor_bracket(
            lexicon_transducer,
            punctuation_transducer,
            open_bracket_transducer,
            close_bracket_transducer):

    punctuation_transducer.optionalize()
    open_bracket_transducer.optionalize()
    close_bracket_transducer.optionalize()

    result = hfst.epsilon_fst()
    result.concatenate(open_bracket_transducer)
    result.concatenate(lexicon_transducer)
    result.concatenate(punctuation_transducer)
    result.concatenate(close_bracket_transducer)
    return result


def build_single_token_acceptor(transducers, punctuation_method):

    def _require_transducers(tr_names):
        for tr_name in tr_names:
            assert tr_name in transducers and \
                   isinstance(transducers[tr_name], hfst.HfstTransducer)

    if punctuation_method == 'bracket':
        _require_transducers(
            ['lexicon', 'punctuation', 'open_bracket', 'close_bracket'])
        return build_single_token_acceptor_bracket(
            transducers['lexicon'],
            transducers['punctuation'],
            transducers['open_bracket'],
            transducers['close_bracket'])
    else:
        raise RuntimeError('Unsupported punctuation method: {}'\
                           .format(punctuation_method))


def build_model(transducers,
    punctuation_method='bracket',
    composition_depth=1,
    words_per_window=3):
    """
    Builds a model for the sliding window algorithm:
    - amends the lexicon transducer: adds compounding, morphology and
      historical umlauts;
    - converts the lexicon transducer into a transducer accepting windows of 
      at most `words_per_window` words, with punctuation in between.
    """

    amend_lexicon_transducer(
        transducers['lexicon'],
        transducers['morphology'] if 'morphology' in transducers else None,
        composition_depth)

    space_tr = hfst.fst(' ')
    single_token_acceptor = build_single_token_acceptor(
        transducers, punctuation_method=punctuation_method)
    window_acceptor = single_token_to_window_acceptor(
        single_token_acceptor, space_tr)

    return transducers['error'], window_acceptor

