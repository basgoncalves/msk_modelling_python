function [ subjectFilename ] = getOutputSubject( baseDir )
%GETOUTPUTSUBJECTNAME Summary of this function goes here
%   Detailed explanation goes here
    addpath('shared');
    fp = getFp();

    if baseDir(end) ~= fp
        baseDir = [baseDir fp];
    end
    outputDir = [baseDir 'ceinms' fp 'subjects' fp 'calibrated'];
    if exist(outputDir, 'dir') ~= 7
        mkdir(outputDir)
    end
    
    content = dir([outputDir, '\*.xml']);
    n = length(content(not([content.isdir])));
    
    subjectFilename = [outputDir fp  'calibrated' num2str(n) '.xml'];
end

