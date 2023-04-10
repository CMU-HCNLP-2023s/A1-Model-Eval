# Assignment 1: Model Evaluation

In this assignment, you will **evaluate existing Huggingface models with CheckList**. Hopefully the assignment will help you:

- Get familiar with the basic programming environment setup for playing with NLP models locally.
- Get familiar with HuggingFace (retrieve models, datasets, call models).
- Get familiar with the concept of model evaluation (using CheckList).

## Steps for completing the assignment.

1. **Envoirnment setup.** Setup the virual Python environment so you can use the same version of Python. Here, I show an example of using [Conda](https://conda.io/projects/conda/en/latest/user-guide/getting-started.html#before-you-start) (which I highly recommend):

   ```sh
   # create an environment named eval_env, under the version of python 3.7
   conda create --name eval_env python=3.7
   # start the environment.
   conda activate eval_env
   ```

2. **Install necessary packages.** You can also directly do `pip install -r requirements.txt`, but I will do a quick step-by-step tour to show you the important packages (links are to their installation pages respectively): [HuggingFace Transformers](https://github.com/huggingface/transformers/blob/main/README.md#installation), [Pytorch](https://pytorch.org/get-started/locally/#start-locally), [Jupyter Notebook](https://jupyter.org/install), [CheckList](https://github.com/marcotcr/checklist), [SpaCy](https://spacy.io/).

   ```sh
   # You should make sure you are in the environment when installing packages.
   conda activate eval_env

   # Install Transformers from huggingface
   pip install transformers
   # also install datasets so you can use their data
   pip install datasets
   # Install Pytorch - the underlying deep learning infrustructure
   pip install torch

   # Install Juypyter Notebook, so you run different blocks of code interactively.
   # !! Make sure to use notebook, not juypterlab, as it may not be compatible with CheckList.
   pip install notebook

   # Finally, CheckList
   pip install checklist
   # use the right ipywidgets version
   pip install ipywidgets==7.5

   # These two lines help you use CheckList in Jupyter Notebook. You should still run them if you did `pip install -r requirements.txt`.

   jupyter nbextension install --py --sys-prefix checklist.viewer
   jupyter nbextension enable --py --sys-prefix checklist.viewer

   # make sure you can use SpaCy models.
   python -m spacy download en_core_web_sm
   ```

3. **Start the programming environment**

   ```sh
   # Make sure you are in the right environment
   conda activate eval_env
   # Assuming you have cloned this git repo:
   # git clone $GIT_REPO_URL
   # Make sure you are in the right folder
   cd $PATH_TO_YOUR_LOCAL_REPO
   # start the jupyter notebook
   jupyter notebook
   ```

4. **Start to complete the task in the notebook.** Visit `http://localhost:8888/notebooks/A1-Notebook.ipynb` so you can see your notebook. Follow its steps. Some tips:

   - Read the HuggingFace tutorial: [Quicktour](https://github.com/huggingface/notebooks/blob/main/transformers_doc/en/quicktour.ipynb) to get familiar with model and dataset loading.
   - Read the CheckList [readme and tutotirals](https://github.com/marcotcr/checklist) to understand how to use the package.
      - In particular, [this tutorial](https://github.com/marcotcr/checklist/blob/master/notebooks/tutorials/4.%20The%20CheckList%20process.ipynb) shows you how to run the Test Suite using Transformer pipelines, which is what you will be doing in your assignment; But all the other tutorials also give you pointers to different functionalities you can use.
   - _Pick NLP task_: (a) Do not use tasks that are already involved in the [CheckList opensource repo](https://github.com/marcotcr/checklist/tree/master/notebooks). However, please feel free to read through the examples to get a sense of how to create your own suite. (b) CheckList is generally easier to use on **Classification** tasks than Generation tasks.
   - _Pick NLP models_: (a) Pick popular and well documented models for a given task. Try their online inference API before downloading them (e.g. [this](https://huggingface.co/bert-base-cased)).
     (b) If you do not have access to GPUs, try to select _small_ models on Huggingface -- check the size of `pytorch_model.bin` (e.g. [here](https://huggingface.co/distilbert-base-uncased-finetuned-sst-2-english/tree/main)). Smaller models are generally less accurate but will make faster predictions.

5. **Write a quick summary of your observations.** Fill in [A1-Summary.md](./A1-Summary.md).

## Delivery

1. Make sure you have finished all of the steps, and have got the `.pkl` file that summarizes your evaluation results.
2. Rename rename `A1-Summary.md` to `A1-Summary-[AndrewID].md` (e.g. `A1-Summary-janedoe.pkl`)
3. Similarly, rename `A1-Suite.pkl` to `A1-Suite-[AndrewID].pkl` (e.g. `A1-Suite-janedoe.pkl`)
4. Create a zip file: `A1-[AndrewID].zip`, that contains both `A1-Summary-[AndrewID].md` and `A1-Test-Suite-[AndrewID].pkl`.
5. Go back to Canvas, and submit `A1-[AndrewID].zip`.

## Grading:

If you find the assignment difficult, there are some ways to earn partial credits, as shown below.

The base grade will be up to 80, based on how you attempt the task:

- **0 point** if no submission.
- **40 points if you attemped the assignment without coding**. In this case, you will fill in the summary in Fill in [A1-Summary-No-Coding.md](./A1-Summary-No-Coding.md) by writing text descriptions of ten tests you'd want to run, rename the file to `A1-Summary-No-Coding-[andrewID].md`, and submit.
- **60 points if you wrote tests for existing tasks** -- i.e., if you submit _modified_ test suites for a task that's already covered in the CheckList repo. However, **if you submit the exact test suite downloaded from CheckList, then it will be considered plagiarism.**
- **70 points if you wrote less than 10 tests for a novel NLP task** (tasks that's not already included in the CheckList repo).
- **80 points if you wrote no less than 10 tests for a novel NLP task** (tasks that's not already included in the CheckList repo).

**The remaining 20 point will be based on peer review results:** (this is similar to CheckList's original user study):

- Three students will rate each of your test on a 1-5 scale: 1) not a bug, 2) minor bug, 3) bug worth investigating and fixing, 4) severe bug, model may not be fit for production, and 5) no model with this bug should be in production.
- Your score depends on the relative ranking of averaged your test score usefulness. you wil get {20, 15, 10, 5} scores if your averaged score is ranked top {25%, 50%, 75%, 100%} percent respectively.

## Questions?

Please post your questions on Canvas.
