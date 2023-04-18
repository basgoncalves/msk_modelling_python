// Create trc file 
// Batch processing in Scilab (version: 6.0.0)

// This code was written by Takuma Inai
// Institute for Human Movement and Medical Sciences
// Niigata University of Health and Welfare

// ===  Unit  ===
// [mm]
// ==============

// === Readme ===
// 1: Please open MarkerNameFile.xls, and write your marker names. 
// 2: Please change DataRate, NumHeaderRowOfInputData, NumRemoveColOfInputData, and Axes_Experiment in this script code.
// 3: Please F5 to execute this script code.
// 4: Please select the folder named CreateFile_trc.
// 5: Please check output data in the folder named OutputFile_trc.
// ==============

clear;
xdel(winsid());
clc;
cd(uigetdir());

//==============================================================================
// Setting
//==============================================================================
DataRate                = 100; // [Hz]

NumHeaderRowOfInputData = 2;
// Please set the number of rows of the header.
// If you do not need to remove some rows, please set '0.'
// Ex: When your csv file has a header including three rows, please set '3.'

NumRemoveColOfInputData = [1,2,3];
// If you want to remove some columns, please set the number of columns. 
// If you do not need to remove some columns, please set '0.'
// Ex: When you want to remove first and second columns, please set '[1, 2].'

Axes_Experiment         = [2,3,1]; // For example: x-axis (right), y-axis (forward), and z-axis (upward) in experiment.
// Note: 1, 2, and 3 indicate x, y, and z axes in this code.
// OpenSim: The x-axis of the model coordinate system points forward from the model, the y-axis points upward, and the z-axis points to the right of the model.

//==============================================================================
// Function
//==============================================================================
function Return = readFile_xls(FileName)
    Sheets = readxls(FileName)
    Return = Sheets(1).text
endfunction
//------------------------------------------------------------------------------
function Return = createRow4(MarkerList)
    [r,c] = size(MarkerList)
    Temp  = ['Frame#' + ascii(9) + 'Time' + ascii(9)]
    for i = 1:r
        Temp = [Temp + MarkerList(i) + ascii(9) + ascii(9) + ascii(9)];
    end
    Return = Temp
endfunction
//------------------------------------------------------------------------------
function Return = createRow5(MarkerList)
    [r,c] = size(MarkerList)
    Temp  = [ascii(9) + ascii(9)]
    XYZ   = ['X','Y','Z']
    for i = 1:r
        for j = 1:3
            Temp = [Temp + XYZ(j) + string(i) + ascii(9)];
        end
    end
    Return = Temp
endfunction
//------------------------------------------------------------------------------
function createFile_trc(InputFileName,MarkerData)

    // Setting (do not need to change)
    PathFileType       = 4
    CameraRate         = DataRate
    NumFrames          = size(MarkerData,1)
    NumMarkers         = size(MarkerList,1)
    Units              = 'mm'
    OrigDataRate       = DataRate
    OrigDataStartFrame = 1
    OrigNumFrames      = NumFrames
    Interval           = 1/DataRate
    Frame              = linspace(1,NumFrames,NumFrames)'
    Time               = linspace(0,(NumFrames-1)*Interval,NumFrames)'
    
    // Remove columns
    if sum(NumRemoveColOfInputData) ~= 0
        MarkerData(:,NumRemoveColOfInputData) = []
    end
    
    // Change axes
    Temp1_MarkerData   = matrix(MarkerData,size(MarkerData,1),3,-1)
    Temp2_MarkerData   = Temp1_MarkerData(:,Axes_Experiment,:)
    NewMarkerData      = matrix(Temp2_MarkerData,size(MarkerData,1),-1)
    
    // Setting output file name and output data (do not need to change)
    PathFileName = strncpy(InputFileList(i),length(InputFileList(i))-4) + '.trc'
    OutputData   = [Frame, Time, NewMarkerData]

    // Header for trc file
    Header     = []
    Header(1)  = ['PathFileType' + ascii(9) + string(PathFileType) + ascii(9) + '(X/Y/Z)' + ascii(9) + PathFileName]
    Header(2)  = ['DataRate' + ascii(9) + 'CameraRate' + ascii(9) + 'NumFrames' + ascii(9) + 'NumMarkers' + ascii(9) + 'Units' + ascii(9) + 'OrigDataRate' + ascii(9) + 'OrigDataStartFrame' + ascii(9) + 'OrigNumFrames']
    Header(3)  = [string(DataRate) + ascii(9) + string(CameraRate) + ascii(9) + string(NumFrames) + ascii(9) + string(NumMarkers) + ascii(9) + Units + ascii(9) + string(OrigDataRate) + ascii(9) + string(OrigDataStartFrame) + ascii(9) + string(OrigNumFrames)]
    Header(4)  = createRow4(MarkerList)
    Header(5)  = createRow5(MarkerList)
    Header(6)  = ['']

    // Output
    csvWrite(OutputData,'OutputFile_trc/' + PathFileName,ascii(9),[],[],Header)

endfunction
//==============================================================================
// Input
//==============================================================================
// Marker list
MarkerList    = readFile_xls('MarkerNameFile.xls');

//==============================================================================
// Batch processing
//==============================================================================
// Setting
InputFileList = ls('InputFile_csv/*.csv');
for i = 1:size(InputFileList,1)
    InputFileList(i) = basename(InputFileList(i)) + fileext(InputFileList(i));
end
NumInputFile  = size(InputFileList,1);

for i = 1:NumInputFile
    // Setting
    InputFileName = InputFileList(i);
    MarkerData    = csvRead('InputFile_csv/' + InputFileName,',',[],[],[],[],[],NumHeaderRowOfInputData); // [mm]
    // Output
    createFile_trc(InputFileName,MarkerData);
end

//==============================================================================

