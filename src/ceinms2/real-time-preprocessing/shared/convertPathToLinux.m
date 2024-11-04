function [ converted ] = convertPathToLinux( path )
%CONVERTPATHTOLINUX Summary of this function goes here
%   Detailed explanation goes here
    expression = '[\\/]+';
    replace = '/';

    converted = regexprep(path,expression,replace);

end

