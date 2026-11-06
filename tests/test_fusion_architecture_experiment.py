import numpy as np
import torch

from scripts.compare_fusion_architectures import EarlyFusion, IntermediateFusion, grouped_case_folds


def test_duplicate_passages_cannot_cross_training_and_evaluation_folds():
    cases=[{'text':f'passage {i//2}'} for i in range(12)]
    held_out=[]
    for train,test in grouped_case_folds(cases):
        assert {cases[i]['text'] for i in train}.isdisjoint({cases[i]['text'] for i in test})
        held_out.extend(test)
    assert sorted(held_out)==list(range(len(cases)))


def test_prototypes_return_one_trainable_score_per_passage_slide_pair():
    torch.manual_seed(42)
    for architecture in [EarlyFusion,IntermediateFusion]:
        model=architecture(8)
        query=torch.randn(4,8);slide=torch.randn(4,8);cues=torch.ones(4,2)
        output=model(query,slide,cues)
        assert output.shape==(4,) and torch.isfinite(output).all()
        output.sum().backward()
        assert any(p.grad is not None and np.isfinite(p.grad.numpy()).all() for p in model.parameters())
