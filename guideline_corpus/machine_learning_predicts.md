# Clinical research

*Source file: Machine-learning-predicts.pdf — extracted verbatim via pdfplumber, column-aware extraction. Original PDF retained in research_papers/ for verification.*

---

Clinical research
Diabetology
Machine learning predicts diabetes risk in high-risk
populations: analysis of National Health and Nutrition
Examination Survey data
Xiaohua Yang1, Meiqi Yao1, Jia Huang2, Zhuojing Cheng2, Ting Sun2*
1N ursing Department, The Second Affiliated Hospital of Zhejiang University School of *Corresponding author:
Medicine, Hangzhou, China Ting Sun
2P hysical Examination Center, The Second Affiliated Hospital of Zhejiang University Physical Examination Center
School of Medicine, Hangzhou, China The Second Affiliated
Hospital
Submitted: 11 June 2025; Accepted: 14 August 2025 of Zhejiang University School
Online publication: 8 September 2025 of Medicine
88 Jiefang Road
Arch Med Sci 2026; 22 (2): 708–720 Shangcheng District
DOI: https://doi.org/10.5114/aoms/209547 Hangzhou, 310009, China
Copyright © 2025 Termedia & Banach Phone: 13906503158
E-mail: 1195037@zju.edu.cn
Abstract
Introduction: This project intended to develop and validate a diabetes prediction model for high-risk populations based on machine learning algorithms.
Material and methods: A total of 2,355 samples from the National Health
and Nutrition Examination Survey (NHANES) database covering three cycles
from 2013 to 2018 were included. The data were divided into training and
testing sets in a 7 : 3 ratio. Nineteen risk prediction factors were selected as
feature variables, including demographic baseline data, measurement data,
medical history, and psychological health. Five machine learning models –
decision tree, random forest (RF), multilayer perceptron (MLP), Adaboost,
and Extreme Gradient Boosting (XGBoost) – were developed based on the
data and variables mentioned above. Model performance was evaluated
using accuracy, sensitivity, specificity, the area under curve (AUC) values
of receiver operating characteristic (ROC) curves, and Matthews Correlation
Coefficient (MCC) scores. Finally, the Shapley feature importance measurement tool was employed to select features in the optimal model.
Results: The present work ultimately included 2,355 individuals at high risk
of diabetes for analysis, with 260 cases of diabetes and 2,095 cases without
diabetes. Among the five machine learning models established in this project., the RF and XGBoost models exhibited better overall performance compared to other models. In the test set, the RF model had an AUC of 0.896, accuracy of 0.784, sensitivity of 0.739, specificity of 0.849, and MCC of 0.418.
The XGBoost model had corresponding values of AUC as 0.903, accuracy of
0.815, sensitivity of 0.962, and MCC of 0.443. According to the importance
analysis of features in these two optimal models, waist circumference, age,
BMI, gender, systolic blood pressure (SBP), diastolic blood pressure (DBP),
education level, poverty income ratio (PIR), Patient Health Questionnaire
(PHQ)-9 score, and race were the top ten key risk factors for diabetes in the
high-risk population.
Conclusions: The RF and XGBoost machine learning models demonstrated
strong performance in predicting the occurrence of diabetes in high-risk
populations. These models can aid in developing more precise intervention
measures and personalized treatment plans to effectively reduce the incidence of diabetes and related risks in this population.
Key words: diabetes, machine learning, National Health and Nutrition
Examination Survey, prediction model.
Creative Commons licenses: This is an Open Access article distributed under the terms of the Creative Commons
Attribution-NonCommercial-ShareAlike 4.0 International (CC BY -NC -SA 4.0). License (http://creativecommons.org/licenses/by-nc-sa/4.0/).

Machine learning predicts diabetes risk in high-risk populations: analysis of National Health and Nutrition Examination Survey data
Introduction Material and methods
Diabetes is a chronic metabolic disorder char- Data source and study population
acterized by abnormal blood sugar levels, caused
This investigation conducted data analysis usby improper use of insulin or insufficient insulin
ing the NHANES public database, which was essecretion, leading to severe long-term damage
tablished and continuously updated and improved
to multiple organs and body systems (including
by the Centers for Disease Control and Prevention
kidneys, heart, nerves, blood vessels, and eyes)
(CDC) in the United States. The NHANES employs
[1], ultimately becoming a major contributor to
a layered, multi-stage probability sampling methmortality [2]. On a global scale, diabetes has beod to select a nationally representative sample of
come a daunting public health challenge, with its
the population, and collects data through direct
prevalence continuing to rise [3]. From 2021 to
physical examinations, clinical and laboratory
2050, the global burden of diabetes will rise from
tests, personal interviews, and relevant measure-
529 million to 1.31 billion people [4]. Despite the
ment procedures. Relevant questionnaires and
projected dramatic increase in the future diabetic
study protocols can be obtained from the NHANES
population, high-risk individuals often underesofficial webpage on the CDC website [16]. The
timate their own risk of developing the disease
NHANES has obtained ethical approval from the
[5, 6]. Once high-risk individuals progress to con-
National Health Statistics Research Ethics Review
firmed cases, although there are treatment meth-
Committee in the United States, and all particiods available to slow down the progression of the
pants have signed informed consent forms to
disease, there is still a lack of curative treatment
ensure that they understand and agree to particioptions [7]. Considering the high prevalence of dipate in the survey.
abetes and the relatively large size of the high-risk
population [8], it is crucial at a population level to
Participants
further identify risk factors and take preventive
measures before high-risk individuals develop the In this project, we selected a sample of indisease state [9]. dividuals at high risk of diabetes from 29,400
In recent years, the application of machine participants in the NHANES from 2013 to 2018.
learning techniques in the medical field has be- The definition criteria for high-risk groups of dicome increasingly widespread, especially in the abetic patients were those who meet any of
prediction of disease risks and diagnosis, exhibit- the following conditions: (1) age ≥ 40 years old;
ing potential value [10–12]. Utilizing rich clinical
(2) impaired glucose tolerance (fasting glucose
data and advanced algorithms, machine learn-
< 126 mg/dl and 140 mg/dl ≤ OGTT (oral glucose
ing studies based on large-scale databases have
tolerance test) < 200 mg/dl) [17] or abnormal fastbecome a hot topic in diabetes research, aiding
ing glucose (100 mg/dl ≤ fasting glucose < 126
in identifying individuals at risk of diabetes and
mg/dl) [18]; (3) overweight (BMI ≥ 25 kg/m2);
providing personalized prevention and manage-
(4) lack of physical activity (moderate or equivament strategies [13, 14]. For example, a project
lent intensity activity time < 150 min per week);
used five machine learning models – Logistic
(5) family history of diabetes; (6) a history of ges-
Regression, Support Vector Machine, Random
tational diabetes; (7) high blood pressure or taking
Forest (RF), Extreme Gradient Boosted Tree, and
antihypertensive drugs; (8) a history of coronary
Weighted Voting Classifier – to predict diabetes
heart disease; (9) patients with polycystic ovarian
in adolescents and identify factors leading to dicancer syndrome; (10) taking antidepressants for
abetes in adolescents, such as waist circumfermore than 3 months and depression diagnosed
ence, gender, BMI, and leg length [15]. However,
by ICD-10 coding (F32.9 and F33.9). By applying
research on the risk assessment of diabetes in
the above screening criteria, 18,649 individuals at
high-risk populations has not been fully develhigh risk of diabetes were identified. Subsequentoped yet.
ly, 16,294 samples with missing feature data were
Therefore, this project utilized the Nationexcluded, resulting in 2,355 eligible samples that
al Health and Nutrition Examination Survey
met the criteria. These samples were divided into
(NHANES) database with a large sample size to
training and testing sets in a 7 : 3 ratio for the
develop a machine learning-based diabetes risk
construction and evaluation of machine learning
prediction model for high-risk populations. The
prediction models. The specific inclusion process
model was designed to enable early identification
is shown in Figure 1.
of individuals at high risk of diabetes within highrisk populations, facilitating timely preventive and
Outcome variables
therapeutic interventions. This research is of great
significance for reducing the incidence of diabetes Diabetes as the outcome variable was defined
and related complications. as meeting one of the following criteria: (a) diag-
Arch Med Sci 2, April / 2026 709

Xiaohua Yang, Meiqi Yao, Jia Huang, Zhuojing Cheng, Ting Sun
A total 29,400 participants included in 2013–2018
cycles in NHANES
Data extraction/Modeling
A total 18,649 participants at high risk of diabetes
16,294 participants with missing data
on features were excluded
A total of 2,355 participants with no missing feature
values were included in the study
Model development
Training data SMOTEENN Testing data
Train Validate
Decision tree
Random forest
MLP
Adaboost
XGBoost
Predictive models
Figure 1. Flow chart illustrating the data processing and model development process
nosed with diabetes by a doctor; (b) taking anti- 9 items rated on a 0–3 scale (0 = “not at all”,
diabetic medication; (c) glycosylated hemoglobin 1 = “a few days”, 2 = “more than half the days”,
HbA > 6.5%; (d) fasting blood glucose > 126 mg/dl and 3 = “almost every day”), yielding a total score
1c
[19, 20]. In this project, the outcome variable of 0–27 points [25, 26].
was defined as a categorical variable, encoded in
numerical form for binary classification of high- Machine learning
risk individuals: 0 indicating non-diabetes and
We applied five machine learning algorithms to
1 indicating diabetes. Categorical features were
train the classification model. The first one was
encoded with numerical values for analysis.
the decision tree, a classification model based
on a tree-like structure, which was used to make
Feature variables
decisions by progressively splitting the data into
The feature variables in this project included multiple nodes. The decision tree model is easy to
demographic baseline data, measurement data, understand and interpret, and suitable for hanmedical history, and the Patient Health Question- dling non-linear relationships and complex rules
naire (PHQ)-9. Demographic baseline data includ- in data [27]. Random forest (RF) is an ensemble
ed gender, age, race, education level [21], poverty- learning model that reduces errors and improves
income ratio (PIR), and family history of diabetes. prediction reliability by constructing multiple in-
Measurement data included waist circumference, dependent decision trees (similar to a flowchart
BMI, diastolic blood pressure (DBP), and systolic judgment model) and then synthesizing the reblood pressure (SBP). History of disease includ- sults of all trees [28]. Multilayer perceptron (MLP)
ed heart disease, hypertension, arthritis, cancer, is a network model that simulates the connecstroke, hearing impairment, vision impairment, tions of human brain neurons. By continuously adasthma, and kidney failure [22, 23]. Kidney failure justing the connection strength of each neuron in
was defined as eGFR ≤ 60 ml/min/1.73 m2 or albu- the network (i.e. a backpropagation algorithm), it
min to creatinine ratio ≥ 30 mg/g [24]. Depression reduces prediction errors and improves the ability
was assessed using the PHQ-9, which includes to judge disease risk [29]. Adaboost, an ensemble
710 Arch Med Sci 2, April / 2026

Machine learning predicts diabetes risk in high-risk populations: analysis of National Health and Nutrition Examination Survey data
learning method, can first train a simple model ranking of features and the relationship between
(weak classifier), then adjust weights based on each feature and the outcome. The SHAP values
its incorrectly predicted samples (making hard-to- for each feature were calculated for each sample
predict samples more noticeable), and then train to reflect the impact of the feature on the predicthe next model, ultimately integrating the results tion result. Next, we aggregated the average abof all models to improve prediction accuracy [30]. solute SHAP values and summarized the global
XGBoost, an efficient gradient boosting algorithm contribution of each feature in a bar chart form
that continuously builds new decision trees to [34]. To address the issue of data imbalance in the
correct errors in previous models, can gradually study, the combination technique of SMOTEENN
improve predictive performance. It is suitable for from the imblearn package was applied to handle
processing complex data and is widely used in imbalanced data. First, we oversampled SMOTE,
classification and regression tasks, with great per- then cleaned the samples with the edited nearest
formance on large-scale datasets [31]. neighbors (ENN) method to reduce noisy samples
and refine model generalization performance [35]
Statistical analysis (p < 0.05: statistically significant).
Continuous variables were presented in the
Results
form of mean and standard deviation, while categorical variables were presented as percentages. Baseline characteristics
We used the t-test for inter-group comparison of
The baseline characteristics included in this
continuous variables and a c2 test for inter-group
project are presented in Table I. With 260 diacomparison of categorical variables. The data
betic patients and 2,095 non-diabetic patients
were split into a 7 : 3 ratio for training and testin high-risk groups, the results indicated that the
ing sets. Machine learning models were developed
average age of those with diabetes was higher
using Python 3.9.7 and the sklearn package [32],
(46.37 vs. 39.15, p < 0.001), and the proportion
and the receiver operating characteristic (ROC)
of people with a high school education level or
curves were plotted using the matplotlib package
equivalent was lower compared with the non-di-
[33]. Five machine learning algorithms – Deciabetic group (46.9% vs. 48.4%, p = 0.020). Waist
sion Tree, RF, MLP, Adaboost, and XGBoost – were
circumference (113.35 vs. 99.32, p < 0.001) and
applied to train the prediction model. The grid
SBP (126.22 vs. 121.06, p < 0.001) in diabetic pasearch method was employed to generate the
tients were significantly higher than those in the
optimal model parameters by adjusting the modunaffected group. Heart disease (9.6% vs. 4.2%),
el parameters for different models and evaluathypertension (68.5% vs. 46.0%, p < 0.001), arthriing their performance. The trained models were
tis (35.4% vs. 20.9%, p < 0.001), stroke (35.4%
evaluated on a test set using 10-fold cross-valivs. 20.9%, p < 0.001), asthma (25.0% vs. 18.5%,
dation to determine the stability of the model.
p = 0.016), chronic kidney disease (23.5% vs.
The following indices were used in evaluation:
9.3%, p < 0.001), hearing loss (11.5% vs. 9.3%, p <
accuracy (the proportion of correct overall mod-
0.001). 5.5%, p < 0.001), and visual loss (12.7% vs.
el predictions), sensitivity (the ability to correctly
5.6%, p < 0.001) were more likely to occur in diaidentify actual patients, that is, the proportion of
betic patients than in unaffected people. In addi-
“no missed diagnosis”), specificity (the ability to
tion, patients with diabetes also showed elevated
correctly identify actual unaffected individuals,
scores of PHQ-9 (5.50 vs. 5.06, p = 0.01).
that is, the proportion of “no misdiagnosis”), the
area under the curve (AUC) of the ROC curves (the
Model performance comparison
comprehensive ability of the model to distinguish
between diseased and non-diseased individuals, Table II shows the performance of five models on
with a value closer to 1 indicating greater ability the test set. The decision tree model had an accurato distinguish patients), and the Matthews cor- cy of 0.744, sensitivity of 0.714, specificity of 0.789,
relation coefficient (MCC), the accuracy of model and AUC of 0.751. In contrast, the RF model had an
classification, ranging from –1 to 1, with the value accuracy of 0.784, sensitivity of 0.739, specificity of
closer to 1 indicating the more reliable ability of 0.849, and AUC of 0.896, exhibiting better perforclassification). Based on the best-performing ma- mance in all aspects. The MLP model had an AUC
chine learning model, the SHAP (SHapley Additive of 0.900 on the test set, with high accuracy (0.822)
exPlanations) model, a tool grounded in mathe- and sensitivity (0.905), but slightly lower specificimatical theory, was used to analyze the impact ty (0.704). The AUC of the AdaBoost model on the
of each factor on the model’s prediction results, test set was 0.895, with a specificity of 0.805 and
identifying more important factors for diabetes good accuracy (0.837) and sensitivity (0.859). The
risk prediction. The partial SHAP values were plot- XGBoost model had an accuracy of 0.815, sensitivited as a summary plot, which included the relative ty of 0.962, specificity of 0.602, and AUC of 0.903 on
Arch Med Sci 2, April / 2026 711

Xiaohua Yang, Meiqi Yao, Jia Huang, Zhuojing Cheng, Ting Sun
Table I. Characteristics of NHANES participants
Characters Total
Overall 2355
Gender
Female 1159 (49.2)
Male 1196 (50.8)
Age 39.95 (11.66)
Race
Mexican American 265 (11.3)
Other Hispanic 200 (8.5)
Non-Hispanic White 1020 (43.3)
Non-Hispanic Black 587 (24.9)
Other race 283 (12.0)
Education level
Less than 9th grade 104 (4.4)
9th to 12th grade (no diploma) 401 (17.0)
High school graduate/GED equivalent 714 (30.3)
Some college or associate degree 848 (36.0)
College graduate or above 288 (12.2)
PIR 2.02 (1.48)
Waist [cm] 100.87 (17.89)
BMI [kg/m2] 28.96 (6.68)
DBP [mm Hg] 72.12 (12.53)
SBP [mm Hg] 121.63 (16.05)
Heart disease
No 2243 (95.2)
Yes 112 (4.8)
Hypertension
No 1214 (51.5)
Yes 1141 (48.5)
Arthritis
No 1826 (77.5)
Yes 529 (22.5)
Cancer
No 2231 (94.7)
Yes 124 (5.3)
Stroke
No 2291 (97.3)
Yes 64 (2.7)
Asthma
No 1902 (80.8)
Yes 453 (19.2)
Chronic kidney disease
No 2100 (89.2)
Yes 255 (10.8)
Hearing loss
No 2210 (93.8)
Yes 145 (6.2)
Vision loss
No 2205 (93.6)
Yes 150 (6.4)
PHQ-9 score 4.39 (5.12)
PIR – poverty income ratio, DBP – diastolic blood pressure, SBP – systol

Non-diabetes Diabetes P-value
2095 (89.0) 260 (11.0)
0.952
1032 (49.3) 127 (48.8)
1063 (50.7) 133 (51.2)
39.15 (11.65) 46.37 (9.62) < 0.001
0.259
227 (10.8) 38 (14.6)
175 (8.4) 25 (9.6)
920 (43.9) 100 (38.5)
524 (25.0) 63 (24.2)
249 (11.9) 34 (13.1)
0.020
85 (4.1) 19 (7.3)
346 (16.5) 55 (21.2)
650 (31.0) 64 (24.6)
757 (36.1) 91 (35.0)
257 (12.3) 31 (11.9)
2.03 (1.49) 1.92 (1.41) 0.260
99.32 (17.21) 113.35 (18.33) < 0.001
29.04 (6.67) 28.27 (6.71) 0.131
71.95 (12.40) 73.46 (13.51) 0.067
121.06 (15.80) 126.22 (17.26) < 0.001
< 0.001
2008 (95.8) 235 (90.4)
87 (4.2) 25 (9.6)
< 0.001
1132 (54.0) 82 (31.5)
963 (46.0) 178 (68.5)
< 0.001
1658 (79.1) 168 (64.6)
437 (20.9) 92 (35.4)
0.408
1988 (94.9) 243 (93.5)
107 (5.1) 17 (6.5)
0.001
2047 (97.7) 244 (93.8)
48 (2.3) 16 (6.2)
0.016
1707 (81.5) 195 (75.0)
388 (18.5) 65 (25.0)
< 0.001
1901 (90.7) 199 (76.5)
194 (9.3) 61 (23.5)
< 0.001
1980 (94.5) 230 (88.5)
115 (5.5) 30 (11.5)
< 0.001
1978 (94.4) 227 (87.3)
117 (5.6) 33 (12.7)
4.27 (5.06) 5.40 (5.50) 0.010
ic blood pressure, PHQ-9 – Patient Health Questionnaire-9.
Arch Med Sci 2, April / 2026

Machine learning predicts diabetes risk in high-risk populations: analysis of National Health and Nutrition Examination Survey data
Table II. Results from 10-fold cross-validation for diabetes classification
Model Accuracy Sensitivity Specificity AUC MCC
Decision tree 0.744 0.714 0.789 0.751 0.361
Random forest 0.784 0.739 0.849 0.896 0.418
MLP 0.822 0.905 0.704 0.900 0.447
Adaboost 0.837 0.859 0.805 0.895 0.463
XGBoost 0.815 0.962 0.602 0.903 0.443
AUC – area under the curve, MCC – Matthews correlation coefficient.
the test set. Compared to MLP and AdaBoost, the and for the XGBoost model was 0.443. The results
XGBoost model had lower specificity but possessed indicated that the Adaboost and MLP models perthe best sensitivity and classification ability. formed well in balancing sensitivity and specific-
Additionally, we calculated the MCC for each ity. However, the MCC results further supported
model to provide a more comprehensive evalua- the conclusion that the RF and XGBoost models
tion of model performance. As shown in Table II, excelled in classification accuracy and recognition
the MCC for the decision tree model was 0.361, capability, respectively. The MCC values of these
for the RF model was 0.418, for the MLP model two models still demonstrated their good classiwas 0.447, for the Adaboost model was 0.463, fication capabilities. Therefore, from an overall as-
A High
Age
Waist
BMI
Gender
DBP
Educational level
SBP
PHQ-Score
PIR
Race
Sum of 9 other features
Low
–0.5 –0.4 –0.3 –0.2 –0.1 0 0.1 0.2
SHAP value (impact on model output)
B
Age +0.11
Waist +0.11
BMI +0.06
Gender +0.05
DBP +0.03
Educational level +0.03
SBP +0.02
PHQ-Score +0.02
PIR +0.02
Race +0.01
Sum of 9 other features +0.03
0 0.02 0.04 0.06 0.08 0.10 0.12
Mean (|SHAP value|)
Figure 2. Summary plot and feature importance for SHAP values in the testing set. Summary SHAP plots (A) and
bar plots (B) of the global SHAP values of the RF model
Arch Med Sci 2, April / 2026 713
eulav
erutaeF

Xiaohua Yang, Meiqi Yao, Jia Huang, Zhuojing Cheng, Ting Sun
C High
Waist
Age
BMI
Gender
DBP
SBP
Educational level
PHQ-Score
PIR
Race
Sum of 9 other features
Low
–6 –4 –2 0 2 4 6
SHAP value (impact on model output)
D High
Waist +2.1
Age +1.7
BMI +0.67
Gender +0.61
DBP +0.60
SBP +0.58
Educational level +0.51
PHQ-Score +0.46
PIR +0.37
Race +0.22
Sum of 9 other features +0.48
Low
0 0.5 1.0 1.5 2.0
Mean (|SHAP value|)
Figure 2. Cont. Summary SHAP plots (C) and bar plots (D) of the global SHAP values of the XGBoost model. SHAP
summary plot provides three aspects of information: (1) ranking indicates the relative importance of features;
(2) Color gradients indicate the relative size of each feature, with red indicating high values of the feature (e.g.,
older age) and blue indicating the opposite (e.g., younger age), where females are shown in blue and males in red.
A negative SHAP value indicates a decreased relative risk, whereas a negative SHAP value indicates an increased
relative risk. (3) The discretization of points indicates whether the relationship between each feature and the outcome is linear. The bars show the global SHAP values
PIR – poverty income ratio, DBP – diastolic blood pressure, SBP – systolic blood pressure, PHQ – Patient Health Questionnaire.
714 Arch Med Sci 2, April / 2026
eulav
erutaeF
sessment of model performance, RF and XGBoost the next most important features. Similarly, in the
were the top-performing models. XGBoost model, the top three features were waist
circumference (SHAP = 2.1), age (SHAP = 1.7), and
Feature importance BMI (SHAP = 0.67), while sex, DBP, SBP, education level, PHQ score, PIR, and race were the next
Based on the comparison of model performance
most important features (Figures 2 C, D). In the
above, we employed RF and XGBoost to calculate
RF and XGBoost models, waist circumference, age,
the importance of each feature. Figure 2 shows the
BMI, and PHQ-9 score were positively correlated
impact of the baseline values of the top 10 feawith diabetes risk, while education level and PIR
tures on the model output, i.e., the development
were negatively correlated with diabetes risk, and
of relative risk for diabetes. Combining the SHAP
women had a higher diabetes risk relative to men.
summary plot (Figure 2 A) with the bar plot (Figure
2 B), the top three features in the RF model were
Discussion
age (SHAP = 0.11), waist circumference (SHAP =
0.11), and BMI (SHAP = 0.06), while sex, DBP, edu- In this project, 2,355 individuals at high risk of
cation level, SBP, PHQ-9 score, PIR, and race were diabetes from the NHANES dataset in the years

Machine learning predicts diabetes risk in high-risk populations: analysis of National Health and Nutrition Examination Survey data
2013–2018 were included to develop the risk positive screening to reduce misdiagnosis rates
model. We applied five machine learning methods and avoid wasting limited medical resources on
(decision tree, RF, MLP, Adaboost, and XGBoost) false-positive individuals. This two-stage strategy
and evaluated their performance, finding that (XGBoost preliminary screening + RF verification)
the AUC values of the RF and XGBoost models in can be effectively integrated into the existing manthe test set were 0.896 and 0.903, respectively. agement process of high-risk groups of diabetes.
The accuracy of the RF model on the test set was More specifically, the XGBoost model is used to
0.784, with sensitivity of 0.739 and specificity of quickly identify a large number of potential high-
0.849, while the XGBoost model had an accuracy risk individuals in community physical examinaof 0.815, with sensitivity of 0.962, indicating that tion, health file system organization, or outpatient
these two machine learning algorithms possessed preliminary screening. Subsequently, for those
high predictive ability in diabetes risk assessment. who tested positive in the initial screening, the RF
Moreover, the MCC values of the RF and XGBoost model was applied in the clinical environment for
models were 0.418 and 0.443, respectively, fur- more accurate review and risk assessment, and
ther validating their robust classification perfor- intervention priorities were determined based on
mance when handling imbalanced datasets. This the doctor’s judgment. It is worth noting that traalso reinforces the suitability of RF and XGBoost ditional models still have value in specific scenarfor developing personalized diabetes risk assess- ios. Logistic regression often performs robustly in
ment tools. Furthermore, we also conducted fea- external validation sets. In comparisons of modture importance analysis on these two models els such as Bayes logistic regression and decision
and found that waist circumference, age, and BMI trees, logistic regression repeatedly ranks among
were closely linked to the development of diabe- the top three [40], but its performance may be
tes, while gender, SBP, DBP, education level, PIR, limited when dealing with nonlinear relationships
PHQ score, and race were identified as import- [41]. Meanwhile, support vector machines (SVM)
ant predictive factors. The present work provided are comparable to the optimal model in certain
important insights for innovating personalized tasks (such as AUROC 0.83) [42], but most studies
disease risk assessment tools in the future, with show that their performance is slightly inferior to
great potential to refine the early prevention and RF or XGBoost [43, 44].
management of diabetes. This study found that BMI, age, waist circum-
In this study, XGBoost performed the best in ference, and depression were positively correlatoverall performance with its gradient boosting ed with diabetes in high-risk groups, and these
architecture, which is consistent with the conclu- key predictors were highly consistent with the
sions of multiple studies. For example, XGBoost existing literature on diabetes risk. Firstly, waist
achieved an AUROC of 0.92 in health literacy circumference, as a core index to measure abdomprediction and nutrition score modeling, outper- inal obesity, was identified as the most important
forming RF (0.90) and logistic regression (0.88), predictor (the highest SHAP value) in the RF and
and leading in sensitivity (91%), specificity (84%), XGBoost models of this study, which is consistent
and other indicators [36]. Another NHANES study with a large body of evidence that abdominal
showed that the AUC of XGBoost (0.8168) was visceral fat is the core pathophysiological mechasignificantly higher than that of RF and logistic nism of diabetes [45]. The visceral adipose tissue
regression (about 0.79), and the three were sim- has strong metabolic activity and secretes a large
ilar in accuracy (about 85%) [37]. In addition, in amount of pro-inflammatory factors and free
the Patient Generated Subject Global Assessment fatty acids, directly leading to insulin resistance
(PG-SGA) score prediction, the AUC values of and β-cell dysfunction [45, 46]. Secondly, age, as
XGBoost and RF were 0.75 and 0.77, respective- a non-modifiable risk factor, has been consistently
ly, showing the best performance [38]. The high associated with the development of disease [47,
sensitivity of XGBoost (> 96% in this study) makes 48]. This study again supported the key role of
it an ideal tool for preliminary screening of large- β-cell function decline and insulin sensitivity descale populations, minimizing missed diagnosis cline in the development of diabetes during aging
rates to the greatest extent possible. In contrast, [49, 50]. Thirdly, as an indicator of overall obealthough RF has slightly lower AUC (0.896) and sity, BMI has a strong association with diabetes
sensitivity (0.739) than XGBoost, its specificity [51–53]. This study confirmed that BMI is still an
(0.849) is significantly higher. This “low false pos- important risk marker in high-risk groups. Obesiitive” advantage stems from its ability to capture ty (whether overall or abdominal) promotes the
non-linear relationships and feature interactions development of diabetes by increasing pancreat-
[39]. Therefore, the RF model is more suitable for ic fat deposition, increasing the burden of β cells,
clinical diagnosis, such as conducting secondary and systemic insulin resistance [54, 55]. Finally,
validation on individuals with XGBoost initial this study found that depression is an important
Arch Med Sci 2, April / 2026 715

Xiaohua Yang, Meiqi Yao, Jia Huang, Zhuojing Cheng, Ting Sun
psychosocial risk factor, which is consistent with lower intervention thresholds. For the population
previous research [56, 57]. It is worth noting that using long-term antidepressant therapy, medical
this study not only confirmed the risk of depres- institutions should establish a linkage mechanism
sion, but also included the screening criterion of between medication and blood glucose monitor-
“continuous use of antidepressant drugs for more ing, and blood glucose indicators should be incorthan 3 months.” The results also suggest that this porated into the routine evaluation system for depopulation has a higher risk, which is consistent pression treatment [61]. Through a combination
with the literature exploring the possible impact of clinical practice and public health measures,
of antidepressant drug use on blood glucose con- risk prediction can be transformed into active pretrol [58]. vention to ultimately reduce the incidence rate of
The positive correlation of BMI, age, waist cir- diabetes and the burden of related complications.
cumference, and depression with the risk of dia- In this study, SBP and DBP were also found to
betes in high-risk groups not only provides strong be associated with the risk of diabetes. Multiple
support for the study of diabetes risk mechanisms population studies have confirmed the universalbut also has a clear application value in clinical ity of this association. Among African Americans
practice and public health. From the perspective and Caucasians aged 35–54, higher blood pressure
of clinical practice, these key predictors can direct- is associated with a higher risk of diabetes comly guide the hierarchical management and precise pared with normal blood pressure [62]. The Koreintervention of high-risk groups. First, waist cir- an adult cohort study showed that even for peocumference can be included in the core indicators ple in prehypertension (120–139/80–89 mm Hg),
of routine screening of high-risk groups of diabetes their risk of diabetes was significantly higher than
in clinical practice, and individuals with markedly that of normotension [63]. These studies indicate
high waist circumference should be prioritized for that blood pressure management should not be
in-depth tests such as fasting blood glucose and limited to patients with diagnosed hypertension.
glycosylated hemoglobin. At the same time, tar- Blood pressure monitoring of high-risk groups (ingeted abdominal fat reduction programs should cluding early status) should be the core component
be developed, such as combining diet control and of diabetes prevention strategies. In addition, race
core muscle group training, to reduce the risk of has been identified as a key sociobiological preinsulin resistance caused by visceral fat deposition dictor. American data show that the prevalence of
[59]. Secondly, in response to the non-modifiable diabetes among non-Hispanic blacks, Asians, and
risk factor of aging, in clinical practice, it is neces- Hispanics (12–14%) is significantly higher than
sary to strengthen regular follow-up for high-risk that of other ethnic groups [64], and this differpopulations over 40 years old, especially focusing ence persists among high-risk elderly people [65].
on their blood glucose fluctuations and changes It suggests that when developing public health inin β-cell function. Early initiation of lifestyle inter- terventions, it is important to focus on high-risk
ventions can delay the decline of β-cell function. racial/ethnic groups and integrate culturally sen-
Thirdly, for individuals with high BMI, weight man- sitive support programs in community screening
agement should be the core intervention goal, and health management.
achieved through personalized nutrition guidance In our study, women in high-risk groups showed
and exercise prescriptions to reduce pancreatic a higher risk of developing diabetes compared to
fat burden and improve insulin sensitivity [60]. men. This is closely related to the physiological
Fourthly, for high-risk populations with depres- changes unique to women, especially the lack of
sion and long-term use of antidepressants, psy- estrogen during menopause. Premature menochiatric and endocrinology departments should pause (< 40 years old) or surgical menopause
collaborate to evaluate and prioritize the selec- significantly increases the risk of type 2 diabetes
tion of antidepressants with a minimal impact on [66, 67]. Estrogen deficiency affects the developblood sugar. At the same time, regular monitoring ment of diabetes through multiple mechanisms,
of glycated hemoglobin and fasting blood sugar including changes in insulin secretion of pancreatshould be conducted to avoid adverse effects of ic β cells, decreased sensitivity of targeted organs
medication on blood sugar control. In addition, and tissues to insulin, and increased sensitivity
from the perspective of public health applications, of major organs of diabetes-related pathology to
a simple risk scoring tool can be developed based glucose [67]. In addition, in an epidemiological
on waist circumference, age, BMI, and depression study, the risk of insomnia in women of all ages
status to enable primary healthcare institutions was found to be generally 40% higher than that
to quickly identify high-risk individuals. For high- in men, and there is a close relationship between
risk subgroups such as the elderly who are easily insomnia and diabetes [68]. Sleep disorders are
overlooked, theme health education should be im- closely related to obesity and insulin resistance
plemented by combining community resources to [69]. Lack of sleep can disrupt key hormones that
716 Arch Med Sci 2, April / 2026

Machine learning predicts diabetes risk in high-risk populations: analysis of National Health and Nutrition Examination Survey data
regulate appetite and energy balance (such as such dynamic effects based on the cross-sectional
leptin, ghrelin, and adiponectin), increase intake data. Future research needs to adopt a prospecof high-calorie foods, and worsen blood sugar tive cohort design, combined with time series
control [70–72]. This suggests that diabetes risk analysis, to more accurately clarify the causal path
screening should routinely include women’s repro- between various risk factors and the onset of diaductive history (such as menopausal age, surgical betes. Secondly, although the feature variables inmenopause history) and sleep quality evaluation. cluded in this study cover multidimensional infor-
At the same time, for perimenopausal and post- mation, key predictive factors may still have been
menopausal women, weight management and overlooked. In the future, genetic data, physical
education and support for lifestyle intervention activity monitoring data, dietary habits, and other
(healthy diet, regular exercise) should be strength- information can be further integrated to improve
ened. the predictive accuracy of the model. In addition,
Education level and income are equally cru- considering the high specificity of the RF model
cial social determinants. High levels of education and the high sensitivity of the XGBoost model,
typically promote healthier lifestyles, reduce shift the exploration of the integration algorithm of the
work (lowering stress and obesity risk), and en- two may further optimize the classification perforhance health awareness and proactive prevention mance, balancing the missed diagnosis rate and
behaviors [73–76]. Conversely, low income and misdiagnosis rate. Finally, this study only evaluatpoverty significantly increased the risk of dia- ed the performance of the model through internal
betes (the probability increased 2–3 times) [77]. validation, and external generalizability still needs
Improving the socio-economic environment (such to be verified. In the future, external validation
as moving out of high poverty areas) can reduce should be conducted among different populathe prevalence of diabetes [78]. Poverty is often tions, especially focusing on the applicability of
accompanied by resource limitations such as mal- the model in resource-limited areas and undernutrition and lack of safe exercise space, exacer- served populations. Based on the above direction,
bating risk factors such as obesity [79]. Therefore, future research can further develop a personalized
for interventions in groups at high risk of diabetes, risk assessment tool that integrates multi-source
we must pay attention to improving the health lit- data, assisting medical personnel and patients
eracy of low-education/low-income groups, and to make joint decisions, ultimately achieving the
provide culturally appropriate and easy-to-under- transformation from risk prediction to accurate
stand educational materials and support services. prevention, and especially providing feasible solu-
At the same time, a sound social security system tions for diabetes prevention and control in reshould be established to ensure their access to source-scarce regions to promote the fairness of
nutrition and basic medical services, and create global diabetes prevention.
a supportive environment to encourage physical
exercise [80]. Funding
This study showed that the RF and XGBoost
No external funding.
models had the best risk prediction performance
among groups with high-risk diabetes, effective-
Ethical approval
ly identifying key risk factors such as waist circumference, age, BMI, depression, SBP, and DBP, Not applicable.
as well as socioeconomic factors such as gender,
education level, and income. These findings sup- Conflict of interest
port the development of RF and XGBoost models
The authors declare no conflict of interest.
as personalized risk assessment tools that can be
embedded in electronic health records systems or
mobile health applications to assist clinicians in
References
achieving risk stratification management, improv-
1. World Health Organization. Diabetes. 2023. Available
ing the efficiency of early screening and intervenfrom: https://www.who.int/news-room/fact-sheets/detion for diabetes, and ultimately reducing the incitail/diabetes.
dence rate and burden of complications. 2. Shin J, Kim J, Lee C, et al. Development of various dia-
However, this study also has some limitations. betes prediction models using machine learning tech-
Firstly, the study adopted a cross-sectional design niques. Diabetes Metab J 2022; 46: 650-7.
and cannot directly infer causal relationships. 3. Liu T, Zhao J, Lin C. Sprouty-related proteins with EVH1
domain (SPRED2) prevents high-glucose induced endo-
Compared to longitudinal studies that can reveal
thelial-mesenchymal transition and endothelial injury
the temporal correlation of disease occurrence
by suppressing MAPK activation. Bioengineered 2022;
through long-term follow-up data (such as track-
13: 13882-92.
ing changes in blood glucose and dynamic evolu- 4. Collaborators GBDD. Global, regional, and national burden
tion of risk factors), this study failed to capture of diabetes from 1990 to 2021, with projections of preva-
Arch Med Sci 2, April / 2026 717

Xiaohua Yang, Meiqi Yao, Jia Huang, Zhuojing Cheng, Ting Sun
lence to 2050: a systematic analysis for the Global Burden
of Disease Study 2021. Lancet 2023; 402: 203-34.
5. Vornanen M, Konttinen H, Peltonen M, Haukkala A. 2
Diabetes and cardiovascular disease risk perception
and risk indicators: a 5-year follow-up. Int J Behav Med
2021; 28: 337-48.
6. Adriaanse MC, Twisk JW, Dekker JM, et al. Perceptions of
risk in adults with a low or high risk profile of developing type 2 diabetes; a cross-sectional population-based 2
study. Patient Educ Couns 2008; 73: 307-12.
7. Naina Marikar S, Al-Hasani K, Khurana I, et al. Pharmacological inhibition of human EZH2 can influence a re- 2
generative beta-like cell capacity with in vitro insulin
release in pancreatic ductal cells. Clin Epigenetics 2023;
15: 101.
8. Walther F, Heinrich L, Schmitt J, Eberlein-Gonska M,
Roessler M. Prediction of inpatient pressure ulcers 2
based on routine healthcare data using machine learning methodology. Sci Rep 2022; 12: 5044.
9. Gong Q, Zhang P, Wang J, et al. Morbidity and mortality 2
after lifestyle intervention for people with impaired glucose tolerance: 30-year results of the Da Qing Diabetes
Prevention Outcome Study. Lancet Diabetes Endocrinol 2
2019; 7: 452-61.
10. Lynch CJ, Liston C. New machine-learning technologies
for computer-aided diagnosis. Nat Med 2018; 24: 1304-5.
11. Johnson KW, Torres Soto J, Glicksberg BS, et al. Artificial intelligence in cardiology. J Am Coll Cardiol 2018; 2
71: 2668-79.
12. Myszczynska MA, Ojamies PN, Lacoste AMB, et al. Applications of machine learning to diagnosis and treatment 2
of neurodegenerative diseases. Nat Rev Neurol 2020;
16: 440-56.
13. Deberneh HM, Kim I. Prediction of type 2 diabetes
based on machine learning algorithm. Int J Environ Res 3
Public Health 2021; 18: 3317.
14. Olusanya MO, Ogunsakin RE, Ghai M, Adeleke MA. Accuracy of machine learning classification models for the
prediction of type 2 diabetes mellitus: a systematic survey and meta-analysis approach. Int J Environ Res Public 3
Health 2022; 19: 14280.
15. Hu H, Lai T, Farid F. Feasibility study of constructing
a screening tool for adolescent diabetes detection applying machine learning methods. Sensors (Basel) 2022; 3
22: 6155.
16. Centers for Disease Control and Prevention. National Health and Nutrition Examination Survey. Available
from: http://www.cdc.gov/nchs/nhanes.htm.
17. Expert Committee on the Diagnosis and Classification 3
of Diabetes Mellitus. Report of the expert committee
on the diagnosis and classification of diabetes mellitus.
Diabetes Care 2003; 26 Suppl. 1: S5-20.
18. Genuth S, Alberti KG, Bennett P, et al. Follow-up report
on the diagnosis of diabetes mellitus. Diabetes Care 3
2003; 26: 3160-7.
19. Hajian-Tilaki K, Heidari B, Hajian-Tilaki A. Are gender differences in health-related quality of life attributable to
sociodemographic characteristics and chronic disease 3
conditions in elderly people? Int J Prev Med 2017; 8: 95.
20. Zhu C, Zhang H, Shen Z, et al. Cystatin C-based estimated GFR performs best in identifying individuals with
poorer survival in an unselected Chinese population: 3
results from the China Health and Retirement Longitudinal Study (CHARLS). Clin Kidney J 2022; 15: 1322-32.
21. Patel JS, Oh Y, Rand KL, et al. Measurement invariance of
the patient health questionnaire-9 (PHQ-9) depression 3
screener in U.S. adults across sex, race/ethnicity, and

education level: NHANES 2005-2016. Depress Anxiety
2019; 36: 813-23.
22. Ferguson JM, Jacobs J, Yefimova M, Greene L, Heyworth L, Zulman DM. Virtual care expansion in the
Veterans Health Administration during the COVID-19
pandemic: clinical services and patient characteristics
associated with utilization. J Am Med Inform Assoc
2021; 28: 453-62.
23. Walker EA, Mertz CK, Kalten MR, Flynn J. Risk perception
for developing diabetes: comparative risk judgments of
physicians. Diabetes Care 2003; 26: 2543-8.
24. Sakhuja S, Jaeger BC, Akinyelure OP, et al. Potential impact of systematic and random errors in blood pressure
measurement on the prevalence of high office blood
pressure in the United States. J Clin Hypertens (Greenwich) 2022; 24: 263-70.
25. Kroenke K, Spitzer RL, Williams JB. The PHQ-9: validity of
a brief depression severity measure. J Gen Intern Med
2001; 16: 606-13.
26. Li W, Zeng L, Yuan S, et al. Machine learning for the prediction of cognitive impairment in older adults. Front
Neurosci 2023; 17: 1158141.
27. Haque UM, Kabir E, Khanam R. Early detection of paediatric and adolescent obsessive-compulsive, separation
anxiety and attention deficit hyperactivity disorder
using machine learning algorithms. Health Inf Sci Syst
2023; 11: 31.
28. KDnuggets. Random Forests®, Explained. 2017. Available from: https://www.kdnuggets.com/2017/10/random-forests-explained.html.
29. Mohammed M, Munir M, Aljabr A. Prediction of date
fruit quality attributes during cold storage based on
their electrical properties using artificial neural networks models. Foods 2022; 11: 1666.
30. Ullah Z, Saleem F, Jamjoom M, Fakieh B. Reliable prediction models based on enriched data for identifying
the mode of childbirth by using machine learning methods: development study. J Med Internet Res 2021; 23:
e28856.
31. Bavaro DA, Fanizzi A, Iacovelli S, et al. A machine learning approach for predicting capsular contracture after
postmastectomy radiotherapy in breast cancer patients.
Healthcare (Basel) 2023; 11: 1042.
32. Ferre F, Laurent R, Furelau P, et al. Perioperative risk assessment of patients using the MyRISK digital score
completed before the preanesthetic consultation: prospective observational study. JMIR Perioper Med 2023;
6: e39044.
33. Chen W, Zhang L, Cai G, et al. Machine learning-based
multimodal MRI texture analysis for assessing renal
function and fibrosis in diabetic nephropathy: a retrospective study. Front Endocrinol (Lausanne) 2023; 14:
1050078.
34. Liu X, Morelli D, Littlejohns TJ, Clifton DA, Clifton L. Combining machine learning with Cox models to identify
predictors for incident post-menopausal breast cancer
in the UK Biobank. Sci Rep 2023; 13: 9221.
35. Yu S, Zhang M, Ye Z, Wang Y, Wang X, Chen YG. Development of a 32-gene signature using machine learning for
accurate prediction of inflammatory bowel disease. Cell
Regen 2023; 12: 8.
36. Inceoglu F, Deniz S, Yagin FH. Prediction of effective sociodemographic variables in modeling health literacy:
a machine learning approach. Int J Med Inform 2023;
178: 105167.
37. Riveros Perez E, Avella-Molano B. Learning from the
machine: is diabetes in adults predicted by lifestyle
Arch Med Sci 2, April / 2026

Machine learning predicts diabetes risk in high-risk populations: analysis of National Health and Nutrition Examination Survey data
variables? A retrospective predictive modelling study of ter-randomised trial. Lancet Diabetes Endocrinol 2020;
NHANES 2007-2018. BMJ Open 2025; 15: e096595. 8: 939-48.
38. Qian G, Jiaxin H, Minghua C, et al. Rapid identification 56. Mezuk B, Eaton WW, Albrecht S, Golden SH. Depression
of tumor patients with PG-SGA ≥ 4 based on machine and type 2 diabetes over the lifespan: a meta-analysis.
learning: a prospective study. BMC Cancer 2025; 25: 902. Diabetes Care 2008; 31: 2383-90.
39. Zhang Y, Zhang X, Razbek J, et al. Opening the black box: 57. Rubin RR, Ma Y, Marrero DG, et al. Elevated depression
interpretable machine learning for predictor finding of symptoms, antidepressant medicine use, and risk of demetabolic syndrome. BMC Endocr Disord 2022; 22: 214. veloping diabetes during the diabetes prevention pro-
40. Qi J, Lei J, Li N, et al. Machine learning models to predict gram. Diabetes Care 2008; 31: 420-6.
in-hospital mortality in septic patients with diabetes. 58. Kammer JR, Hosler AS, Leckman-Westin E, DiRienzo G,
Front Endocrinol (Lausanne) 2022; 13: 1034251. Osborn CY. The association between antidepressant use
41. Chu WM, Tsan YT, Chen PY, et al. A model for predicting and glycemic control in the Southern Community Cophysical function upon discharge of hospitalized older hort Study (SCCS). J Diabetes Complications 2016; 30:
adults in Taiwan-a machine learning approach based 242-7.
on both electronic health records and comprehensive 59. Russell LE, Tse J, Bowie J, et al. Cooking behaviours afgeriatric assessment. Front Med (Lausanne) 2023; 10: ter Diabetes Prevention Program (DPP) participation
1160013. among DPP participants in Baltimore, MD. Public Health
42. Rus Prelog P, Matic T, Pregelj P, Sadikov A. A pilot predic- Nutr 2023; 26: 2492-7.
tive model based on COVID-19 data to assess suicidal 60. Crandall JP, Dabelea D, Knowler WC, Nathan DM, Temideation indirectly. J Psychiatr Res 2023; 163: 318-24. prosa M, Group DPPR. The diabetes prevention program
43. Obagbuwa IC, Danster S, Chibaya OC. Supervised ma- and its outcomes study: NIDDK’s journey into the prechine learning models for depression sentiment analy- vention of type 2 diabetes and its public health impact.
sis. Front Artif Intell 2023; 6: 1230649. Diabetes Care 2025; 48: 1101-11.
44. Asnake AA, Gebrehana AK, Asebe HA, et al. Application 61. Murteira R, Cary M, Galante H, Romano S, Guerreiro JP,
of machine learning algorithm for prediction of abor- Rodrigues AT. Effectiveness of a collaborative diabetes
tion among reproductive age women in Ethiopia. Sci screening campaign between community pharmacies
Rep 2025; 15: 17924. and general practitioners. Prim Care Diabetes 2023; 17:
45. Sam S. Differential effect of subcutaneous abdominal 314-20.
and visceral adipose tissue on cardiometabolic risk. 62. Wei GS, Coady SA, Goff DC, et al. Blood pressure and
Horm Mol Biol Clin Investig 2018; 33. the risk of developing diabetes in african americans and
46. Joshi RD, Dhakal CK. Predicting type 2 diabetes using lo- whites: ARIC, CARDIA, and the framingham heart study.
gistic regression and machine learning approaches. Int Diabetes Care 2011; 34: 873-9.
J Environ Res Public Health 2021; 18: 7346. 63. Cho NH, Kim KM, Choi SH, et al. High blood pressure and
47. Meshram, II, Vishnu Vardhana Rao M, Sudershan Rao V, its association with incident diabetes over 10 years in
Laxmaiah A, Polasa K. Regional variation in the preva- the Korean Genome and Epidemiology Study (KoGES).
lence of overweight/obesity, hypertension and diabetes Diabetes Care 2015; 38: 1333-8.
and their correlates among the adult rural population in 64. Menke A, Casagrande S, Geiss L, Cowie CC. Prevalence
India. Br J Nutr 2016; 115: 1265-72. of and trends in diabetes among adults in the United
48. De Tata V. Age-related impairment of pancreatic be- States, 1988-2012. JAMA 2015; 314: 1021-9.
ta-cell function: pathophysiological and cellular mecha- 65. Odlum M, Moise N, Kronish IM, et al. Trends in poor
nisms. Front Endocrinol (Lausanne) 2014; 5: 138. health indicators among black and hispanic mid-
49. Hernandez-Bautista RJ, Alarcon-Aguilar FJ, Del CE-VM, dle-aged and older adults in the United States, 1999-
et al. Biochemical alterations during the obese-aging 2018. JAMA Netw Open 2020; 3: e2025134.
process in female and male monosodium glutamate 66. Shen L, Song L, Li H, et al. Association between earlier
(MSG)-treated mice. Int J Mol Sci 2014; 15: 11473-94. age at natural menopause and risk of diabetes in mid-
50. Lee JH, Lee J. Endoplasmic reticulum (ER) stress and its dle-aged and older Chinese women: the Dongfeng-Tongrole in pancreatic beta-cell dysfunction and senescence ji cohort study. Diabetes Metab 2017; 43: 345-50.
in type 2 diabetes. Int J Mol Sci 2022; 23: 4843. 67. Mauvais-Jarvis F, Manson JE, Stevenson JC, Fonseca VA.
51. Par F, Sarvi F, Khodadost M, Pezeshki B, Doosti H, Ta- Menopausal hormone therapy and type 2 diabetes
brizi R. A nonlinear association of body mass index and prevention: evidence, mechanisms, and clinical implicafasting blood glucose: a dose-response analysis from tions. Endocr Rev 2017; 38: 173-88.
fasa adults cohort study (FACS). Health Sci Rep 2025; 68. Schmid SM, Hallschmid M, Schultes B. The metabolic
8: e70560. burden of sleep loss. Lancet Diabetes Endocrinol 2015;
52. Poulsen K, Cleal B, Clausen T, Andersen LL. Work, dia- 3: 52-62.
betes and obesity: a seven year follow-up study among 69. Cappuccio FP, D’Elia L, Strazzullo P, Miller MA. Quantity
Danish health care workers. PLoS One 2014; 9: e103425. and quality of sleep and incidence of type 2 diabetes:
53. Ng ACT, Delgado V, Borlaug BA, Bax JJ. Diabesity: the a systematic review and meta-analysis. Diabetes Care
combined burden of obesity and diabetes on heart dis- 2010; 33: 414-20.
ease and the role of imaging. Nat Rev Cardiol 2021; 18: 70. Spiegel K, Leproult R, L’Hermite-Baleriaux M, Copinschi G,
291-304. Penev PD, Van Cauter E. Leptin levels are dependent on
54. Skudder-Hill L, Sequeira IR, Cho J, Ko J, Poppitt SD, Pe- sleep duration: relationships with sympathovagal baltrov MS. Fat distribution within the pancreas according ance, carbohydrate regulation, cortisol, and thyrotropin.
to diabetes status and insulin traits. Diabetes 2022; 71: J Clin Endocrinol Metab 2004; 89: 5762-71.
1182-92. 71. Taheri S, Lin L, Austin D, Young T, Mignot E. Short sleep
55. Al-Mrabeh A, Hollingsworth KG, Shaw JAM, et al. 2-year duration is associated with reduced leptin, elevated
remission of type 2 diabetes and pancreas morpholo- ghrelin, and increased body mass index. PLoS Med
gy: a post-hoc analysis of the DiRECT open-label, clus- 2004; 1: e62.
Arch Med Sci 2, April / 2026 719

Xiaohua Yang, Meiqi Yao, Jia Huang, Zhuojing Cheng, Ting Sun
72. Hibi M, Kubota C, Mizuno T, et al. Effect of shortened
sleep on energy expenditure, core body temperature,
and appetite: a human randomised crossover trial. Sci
Rep 2017; 7: 39640.
73. Borrell LN, Dallo FJ, White K. Education and diabetes in
a racially and ethnically diverse population. Am J Public
Health 2006; 96: 1637-42.
74. Hanprathet N, Lertmaharit S, Lohsoonthorn V, Rattananupong T, Ammaranond P, Jiamjarasrangsi W. Increased
risk of type 2 diabetes and abnormal FPG due to shift
work differs according to gender: a retrospective cohort
study among Thai workers in Bangkok, Thailand. Diabetes Metab Syndr Obes 2019; 12: 2341-54.
75. Suwazono Y, Dochi M, Sakata K, et al. A longitudinal
study on the effect of shift work on weight gain in male
Japanese workers. Obesity (Silver Spring) 2008; 16:
1887-93.
76. Allen K, McFarland M. How are income and education
related to the prevention and management of diabetes?
J Aging Health 2020; 32: 1063-74.
77. Dinca-Panaitescu S, Dinca-Panaitescu M, Bryant T, Daiski I, Pilkington B, Raphael D. Diabetes prevalence and
income: results of the Canadian Community Health
Survey Health Policy 2011; 99: 116-23.
78. Ludwig J, Sanbonmatsu L, Gennetian L, et al. Neighborhoods, obesity, and diabetes – a randomized social experiment. N Engl J Med 2011; 365: 1509-19.
79. Gaskin DJ, Thorpe RJ Jr., McGinty EE, et al. Disparities
in diabetes: the nexus of race, poverty, and place. Am
J Public Health 2014; 104: 2147-55.
80. Okwechime IO, Roberson S, Odoi A. Prevalence and predictors of pre-diabetes and diabetes among adults 18
years or older in Florida: a multinomial logistic modeling
approach. PLoS One 2015; 10: e0145781.

Arch Med Sci 2, April / 2026