import scipy.stats as stats
import numpy as np
import pdb
import msk_modelling_python.src.utils as utils

def compar2groups(Y1, Y2, alpha=0.05, TYPE=1):
    """
    Performs a paired or independent t-test or Wilcoxon signed-rank test to compare two groups.

    Args:
        Y1 (array-like): Data for group 1.
        Y2 (array-like): Data for group 2.
        alpha (float, optional): Significance level. Defaults to 0.05.
        TYPE (int, optional): Type of test (1 for paired, 2 for independent). Defaults to 1.

    Returns:
        H (bool): Test statistic.
        P (float): P-value.
        Npvalue (float): Normality p-value (if applicable).
        MD (float): Mean difference.
        uCI (float): Upper confidence interval.
        lCI (float): Lower confidence interval.
    """
    # debug.add_debug_break()
    if TYPE == 1 and len(Y1) == len(Y2):  # Paired T-test
        
        H, Npvalue = stats.shapiro(Y2 - Y1)

        if H == 0:  # Paired T-test
            H, P = stats.ttest_rel(Y1, Y2, alpha=alpha)
        else:  # Wilcoxon signed-rank test
            P, H = stats.ranksums(Y1, Y2, alternative='two-sided', alpha=alpha)

    
    elif TYPE == 2 or not len(Y1) == len(Y2):  # Independent T-test
        H1, Npvalue1 = stats.shapiro(Y1)
        H2, Npvalue2 = stats.shapiro(Y2)
        Npvalue = (Npvalue1, Npvalue2)

        if H1 == 0 and H2 == 0:  # Independent T-test
            H, P = stats.ttest_ind(Y2, Y1, equal_var=False)
        else:  # Wilcoxon signed-rank test
            H, P = stats.ranksums(Y2, Y1)
            

    MD = np.nanmean(Y2) - np.nanmean(Y1)
    # Calculate the standard error
    std_err = np.sqrt(np.var(Y2) / len(Y1) + np.var(Y1) / len(Y1))

    # Calculate the t-statistic
    t_stat = MD / std_err

    # Calculate the degrees of freedom
    dof = len(Y1) + len(Y2) - 2

    # Calculate the confidence interval
    t_crit = stats.t.ppf(1 - alpha / 2, dof)
    lCI = MD - t_crit * std_err
    uCI = MD + t_crit * std_err

    return H, P, Npvalue, MD, std_err, uCI, lCI


def test():
    Y1 = np.array([1, 2, 3, 4, 5])
    Y2 = np.array([6, 7, 8, 9, 10, 12])
    alpha = 0.05
    TYPE = 2
    H, P, Npvalue, MD, std_err, uCI, lCI = compar2groups(Y1, Y2, alpha, TYPE)
    print(f'H: {H}, P: {P}, Npvalue: {Npvalue}, MD: {MD}, uCI: {uCI}, lCI: {lCI}')
    
    print("Test passed!")
    

if __name__ == '__main__':
    Y1 = np.array([1, 2, 3, 4, 5])
    Y2 = np.array([6, 7, 8, 9, 10, 12])
    alpha = 0.05
    TYPE = 2
    H, P, Npvalue, MD, uCI, lCI = compar2groups(Y1, Y2, alpha, TYPE)
    print(f'H: {H}, P: {P}, Npvalue: {Npvalue}, MD: {MD}, uCI: {uCI}, lCI: {lCI}')