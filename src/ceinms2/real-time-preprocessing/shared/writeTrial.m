function [ trialPath ] = writeTrial(trialFilename, lmtFile, excitationsFile,...
    momentArmsFileList, externalTorqueFile,motionFile,externalLoadsFile,TimeWindow)
%WRITETRIAL Summary of this function goes here
%   Detailed explanation goes here
%
%momentArmsFileList has to have the following structure
%momentArmsFileList = {};
%momentArmsFileList{1}.dof = 'dof1';
%momentArmsFileList{1}.file = 'file1';
%momentArmsFileList{2}.dof = 'dof2';
%momentArmsFileList{2}.file = 'file2';
fp = getFp();
useRelativePath = false;
[actualPath,~,~] = fileparts(trialFilename);
trialPath = actualPath;
if useRelativePath
    [path,~,~] = fileparts(mfilename('fullpath'));
    addpath([path fp '..' fp 'relativepath']);

    [lmtPath,lmtName,lmtExt] = fileparts(lmtFile);
    lmtFile = [relativepath(lmtPath, actualPath) lmtName lmtExt];

    [excPath,excName,excExt] = fileparts(excitationsFile);
    excitationsFile = [relativepath(excPath, actualPath) excName excExt];
    
    for i =1:length(momentArmsFileList)
        [maPath,maName,maExt] = fileparts(momentArmsFileList{i}.file);
        momentArmsFileList{i}.file = [relativepath(maPath, actualPath) maName maExt];
    end
    
    [trqPath,trqName,trqExt] = fileparts(externalTorqueFile);
    externalTorqueFile = [relativepath(trqPath, actualPath) trqName trqExt];
end


inputData = [];
inputData.muscleTendonLengthFile = convertPathToLinux(lmtFile);
inputData.excitationsFile = convertPathToLinux(excitationsFile);
for i =1:length(momentArmsFileList)
    inputData.momentArmsFiles.momentArmsFile{i}.ATTRIBUTE.dofName = momentArmsFileList{i}.dof;
    inputData.momentArmsFiles.momentArmsFile{i}.CONTENT = convertPathToLinux(momentArmsFileList{i}.file);
end
inputData.externalTorquesFile = convertPathToLinux(externalTorqueFile);
inputData.motionFile = convertPathToLinux(motionFile);
inputData.externalLoadsFile = convertPathToLinux(externalLoadsFile);

if nargin == 8
    inputData.startStopTime = num2str(TimeWindow);
end


pref.CellItem = false;
xml_write(trialFilename, inputData, 'inputData', pref);

end

