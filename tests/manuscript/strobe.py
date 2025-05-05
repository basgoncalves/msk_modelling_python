# Module to ease the STROBE questionnaire process for a given manuscript
# von Elm, E., Altman, D. G., Egger, M., Pocock, S. J., Gøtzsche, P. C., & Vandenbroucke, J. P. (2007). The Strengthening the Reporting of Observational Studies in Epidemiology (STROBE) statement: guidelines for reporting observational studies. The Lancet, 370(9596), 1453–1457. https://doi.org/10.1016/S0140-6736(07)61602-X
#
# by Basilio Goncalves, 2025
#
# USAGE:
# python strobe.py
# Follow the instructions in the GUI to answer the questions.
# The answers will be saved in a CSV file with the same name as the PDF file, but with "_STROBE.csv" appended to it.
# The CSV file will be saved in the same directory as the PDF file.

import os
import sys
import pandas as pd
import customtkinter as ctk
from tkinter import filedialog, messagebox

def seletect_pdf_file():
    """Open a file dialog to select a PDF file."""
    pdf_path = filedialog.askopenfilename(title="Select the PDF file", filetypes=[("PDF files", "*.pdf")])
    if not pdf_path:
        messagebox.showerror("Error", "No file selected.")
        sys.exit(1)
    return pdf_path

def ask_question(root, question):
    """Display a dialog to ask the user a question and return the answer."""
    answer = None

    def submit_response(response):
        nonlocal answer
        answer = response
        question_window.destroy()

    question_window = ctk.CTkToplevel(root)
    question_window.title("STROBE Question")

    # Dynamically adjust size based on question length
    charachter_size = 1  # Average character size in pixels
    base_width = 400
    base_height = 200
    extra_width_per_char = 0.1  # Additional width per character
    extra_height_per_char = 0.1  # Additional height per character

    question_length = len(question) * charachter_size
    width = base_width + int(question_length * extra_width_per_char)
    height = base_height + int(question_length * extra_height_per_char)

    # Set a maximum size to avoid overly large windows
    max_width = 800
    max_height = 600
    width = min(width, max_width)
    height = min(height, max_height)

    question_window.geometry(f"{width}x{height}")

    # Center the window on the screen
    question_window.update_idletasks()
    screen_width = question_window.winfo_screenwidth()
    screen_height = question_window.winfo_screenheight()
    x = (screen_width - width) // 2
    y = (screen_height - height) // 2
    question_window.geometry(f"+{x}+{y}")
    question_window.grab_set()

    label = ctk.CTkLabel(question_window, text=question, wraplength=width - 50, justify="left")
    label.pack(pady=20)

    button_yes = ctk.CTkButton(question_window, text="Yes", command=lambda: submit_response("Yes"))
    button_yes.pack(side="left", padx=20, pady=20)

    button_no = ctk.CTkButton(question_window, text="No", command=lambda: submit_response("No"))
    button_no.pack(side="right", padx=20, pady=20)

    root.wait_window(question_window)
    return answer

if __name__ == "__main__":
    
    # Set the appearance mode and color theme
    ctk.set_appearance_mode("System")  # Modes: "System" (default), "Dark", "Light"
    
    # Create the main application window and hide it (it will be used only for the dialogs)
    root = ctk.CTk()
    root.withdraw()  

    pdf_path = seletect_pdf_file()
    # Define the questions
    questions = {
        "1": (
            "1 (a) Indicate the study's design with a commonly used term in the title or the abstract\n"
            "(b) Provide in the abstract an informative and balanced summary of what was done and what was found"
        ),
        "2": "Explain the scientific background and rationale for the investigation being reported",
        "3": "State specific objectives, including any prespecified hypotheses",
        "4": "Present key elements of study design early in the paper",
        "5": "Describe the setting, locations, and relevant dates, including periods of recruitment, exposure, follow-up, and data collection",
        "6": (
            "(a) Cohort study—give the eligibility criteria, and the sources and methods of selection of participants. "
            "Describe methods of follow-up\n"
            "Case-control study—give the eligibility criteria, and the sources and methods of case ascertainment and control selection. "
            "Give the rationale for the choice of cases and controls\n"
            "Cross-sectional study—give the eligibility criteria, and the sources and methods of selection of participants\n"
            "(b) Cohort study—for matched studies, give matching criteria and number of exposed and unexposed\n"
            "Case-control study—for matched studies, give matching criteria and the number of controls per case"
        ),
        "7": "Clearly define all outcomes, exposures, predictors, potential confounders, and effect modifiers. Give diagnostic criteria, if applicable",
        "8": (
            "* For each variable of interest give sources of data and details of methods of assessment (measurement). "
            "Describe comparability of assessment methods if there is more than one group"
        ),
        "9": "Describe any efforts to address potential sources of bias",
        "10": "Explain how the study size was arrived at",
        "11": (
            "Explain how quantitative variables were handled in the analyses. If applicable, describe which groupings were chosen, and why"
        ),
        "12": (
            "(a) Describe all statistical methods, including those used to control for confounding\n"
            "(b) Describe any methods used to examine subgroups and interactions\n"
            "(c) Explain how missing data were addressed\n"
            "(d) Cohort study—if applicable, explain how loss to follow-up was addressed\n"
            "Case-control study—if applicable, explain how matching of cases and controls was addressed\n"
            "Cross-sectional study—if applicable, describe analytical methods taking account of sampling strategy\n"
            "(e) Describe any sensitivity analyses"
        ),
        "13": (
            "* (a) Report the numbers of individuals at each stage of the study—eg, numbers potentially eligible, examined for eligibility, "
            "confirmed eligible, included in the study, completing follow-up, and analysed\n"
            "(b) Give reasons for non-participation at each stage\n"
            "(c) Consider use of a flow diagram"
        ),
        "14": (
            "* (a) Give characteristics of study participants (eg, demographic, clinical, social) and information on exposures and potential confounders\n"
            "(b) Indicate the number of participants with missing data for each variable of interest\n"
            "(c) Cohort study—summarise follow-up time (eg, average and total amount)"
        ),
        "15": (
            "* Cohort study—report numbers of outcome events or summary measures over time\n"
            "Case-control study—report numbers in each exposure category, or summary measures of exposure\n"
            "Cross-sectional study—report numbers of outcome events or summary measures"
        ),
        "16": (
            "(a) Give unadjusted estimates and, if applicable, confounder-adjusted estimates and their precision (eg, 95% confidence interval). "
            "Make clear which confounders were adjusted for and why they were included\n"
            "(b) Report category boundaries when continuous variables were categorised\n"
            "(c) If relevant, consider translating estimates of relative risk into absolute risk for a meaningful time period"
        ),
        "17": "Report other analyses done—eg, analyses of subgroups and interactions, and sensitivity analyses",
        "18": "Summarise key results with reference to study objectives",
        "19": (
            "Discuss limitations of the study, taking into account sources of potential bias or imprecision. "
            "Discuss both direction and magnitude of any potential bias"
        ),
        "20": (
            "Give a cautious overall interpretation of results considering objectives, limitations, multiplicity of analyses, "
            "results from similar studies, and other relevant evidence"
        ),
        "21": "Discuss the generalisability (external validity) of the study results",
        "22": (
            "Give the source of funding and the role of the funders for the present study and, if applicable, for the original study "
            "on which the present article is based"
        )
    }

    # Create a DataFrame to store STROBE answers
    strobe = pd.DataFrame(columns=[f"STROBE_{i}" for i in range(1, len(questions) + 1)])

    # Loop through the questions and ask for user input (Limit to first [:XX] questions)
    for key, question in list(questions.items())[:10]: 
        
        # Ask the question and get the answer
        answer = ask_question(root, question)
        
        # Check if the answer is valid (Yes/No)
        if answer is None:  
            messagebox.showerror("Error", "Input canceled.")
            sys.exit(1)
        strobe.at[0, f"STROBE_{key}"] = answer

    # Save the DataFrame to a CSV file
    output_path = pdf_path.replace(".pdf", "_STROBE.csv")

    # Crop the name if needed to avoid long file names
    if len(output_path) > 255:
        base_name = os.path.basename(output_path)
        dir_name = os.path.dirname(output_path)
        cutt_off = 255 - len(dir_name) - 1  # -1 for the separator
        truncated_name = base_name[:cutt_off] + "_STROBE.csv"
        output_path = os.path.join(dir_name, truncated_name)

    try:
        strobe.to_csv(output_path, index=False)
        print(f"STROBE answers saved to {output_path}")
    except Exception as e:
        messagebox.showerror("Error", f"Failed to save the file: {e}")
        sys.exit(1)


# END