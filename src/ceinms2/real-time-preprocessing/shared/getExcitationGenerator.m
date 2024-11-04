function [ outputFilename ] = getExcitationGenerator( baseDir, side )
%GETEXCITATIONGENERATOR Summary of this function goes here
%   Detailed explanation goes here

    fp = getFp();
    [path,~,~] = fileparts(mfilename('fullpath'));
    
    postfix = '-RIGHT';
    if strcmp(side, 'left')
        postfix = '-LEFT';
    end
 %   filename = ['excitationGenerator16to34' postfix '.xml'];
    filename = ['excitationGenerator16to22' postfix '.xml'];
    templateFilename = [path fp '..' fp 'template' fp 'excitationGenerator' fp filename];
    outputDir = [baseDir fp 'ceinms' fp 'excitationGenerator'];
    if (exist(outputDir,'dir') ~= 7)
        mkdir(outputDir);
    end
    
    outputFilename = [outputDir fp filename];
    copyfile(templateFilename,outputFilename);
end

