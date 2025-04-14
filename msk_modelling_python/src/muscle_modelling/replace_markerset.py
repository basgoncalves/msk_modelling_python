from bops import *
import bops as bp
import ceinms_setup as cs
import plot as plt

def export_markerset_osim(osim_path, output_file, markers_to_delete=[]):
    
    def delete_element_by_tag(element, tag):
        for child in element.findall(tag):
            element.remove(child)
    
    def delete_marker_by_name(root, markers_to_delete, output_file):

        # Iterate through each marker name in the list
        for marker_name in markers_to_delete:

            print(f"Deleting marker '{marker_name}'")
            try:
                # Find all Marker tags with the specified name
                markers = root.findall(".//Marker[@name='" + marker_name + "']")
            except Exception as e:
                cs.print_terminal_spaced('Error finding marker: {}'.format(e))
                exit()
            # Remove the found Marker tags
            for marker in markers:
                markers.remove(marker)

        return tree

    try:
        with open(osim_path, 'r', encoding='utf-8') as file:
            tree = ET.parse(osim_path)
            root = tree.getroot()
    except Exception as e:
        cs.print_terminal_spaced('Error opening input file: {}'.format(e))
        exit()
    
      # Find the MarkerSet tag
    try:
        marker_set = root.find('.//MarkerSet')
    except Exception as e:
        cs.print_terminal_spaced('File does not contain MarkerSet tag: {}'.format(e))
        exit()

    if marker_set is not None:
        # Create a new XML tree with only the MarkerSet tag
        new_tree = ET.ElementTree(marker_set)

        delete_marker_by_name(tree, markers_to_delete, output_file)

        # Write the new tree to the output file
        new_tree.write(output_file)
        print(f"MarkerSet copied from '{osim_path}' to '{output_file}'")
    else:
        print("MarkerSet tag not found in the input file.")

def compare_markerset_osim(osim_path1, osim_path2):

    try:
        with open(osim_path1, 'r', encoding='utf-8') as file:
            tree1 = ET.parse(osim_path1)
            root1 = tree1.getroot()
        
        with open(osim_path2, 'r', encoding='utf-8') as file:
            tree2 = ET.parse(osim_path2)
            root2 = tree2.getroot()
    except Exception as e:
        cs.print_terminal_spaced('Error opening input file: {}'.format(e))
        exit()

    # Find the MarkerSet tag
    try:
        marker_set1 = root1.find('.//MarkerSet')
        marker_set2 = root2.find('.//MarkerSet')
    except Exception as e:
        cs.print_terminal_spaced('File does not contain MarkerSet tag: {}'.format(e))
        exit()

    try:
        markers1 = marker_set1.findall('.//Marker')
        markers2 = marker_set2.findall('.//Marker')
        
        marker_names1 = [marker.get('name') for marker in markers1]
        marker_names2 = [marker.get('name') for marker in markers2]
        
        similar_markers = list(set(marker_names1) & set(marker_names2))
        non_similar_markers = list(set(marker_names1) ^ set(marker_names2))

    except Exception as e:
        cs.print_terminal_spaced('Error comparing MarkerSet tags: {}'.format(e))
        exit()

    return similar_markers, non_similar_markers

def add_markerset_to_osim(osim_path, new_opensim_path, markerset_path):
    
    try:
        with open(osim_path, 'r', encoding='utf-8') as file:
            tree = ET.parse(osim_path)
            model_root = tree.getroot()
        
        with open(markerset_path, 'r', encoding='utf-8') as file:
            markerset_tree = ET.parse(markerset_path)
            markerset_root = markerset_tree.getroot()
    except Exception as e:
        cs.print_terminal_spaced('Error opening input file: {}'.format(e))
        exit()

    # Create a new element (markerset_root)
    existing_element = model_root.find('.//MarkerSet')

    # Replace the existing element with the new element
    if existing_element is not None:
        existing_element.clear()
        existing_element.extend(markerset_root)
  
    # Write the new tree to the output file
    try:
        tree.write(new_opensim_path)
        print(f"MarkerSet copied from '{osim_path}' to '{new_opensim_path}'")
    except Exception as e:
        cs.print_terminal_spaced('Error writing output file: {}'.format(e))
        exit()

def reorder_markers(xml_path, order):
    tree = ET.parse(xml_path)
    root = tree.getroot()

    # Create a dictionary to store marker elements by name
    # markers_dict = {marker.find('name').text: marker for marker in root.findall('.//Marker')}

    # Create a new MarkerSet element to replace the existing one
    new_marker_set = ET.Element('MarkerSet')
    # Create the 'objects' element
    objects_element = ET.SubElement(new_marker_set, 'objects')    
    groups_element = ET.SubElement(new_marker_set, 'groups')    

    # Add Marker elements to the new MarkerSet in the specified order
    for marker_name in order:
        existing_marker = root.find('.//Marker[@name="' + marker_name + '"]')
        if existing_marker:
            objects_element.append(existing_marker)

    # Replace the existing MarkerSet with the new one
    existing_marker_set = root.find('.//MarkerSet')
    existing_marker_set.clear()
    existing_marker_set.extend(new_marker_set)

    # Save the modified XML back to a file
    tree.write(xml_path)


if __name__ == '__main__':
    
    # edit bellow
    subject_name = 'Athlete_14' # id code
    torsion_model = True # True or False

    # DO NOT CHANGE
    model_with_generic_markerset = r"C:\Git\isbs2024\Data\Scaled_models\Athlete_03_scaled.osim" # DO NOT CHANGE
    alex_model_complex = r"C:\Git\isbs2024\Data\Scaled_models\Alex\Athlete_03_scaled.osim" # DO NOT CHANGE

    original_osim_path = rf"C:\Git\isbs2024\Data\Scaled_models\Alex\{subject_name}_scaled.osim"
    if torsion_model:
        final_osim_path = rf"C:\Git\isbs2024\Data\Scaled_models\{subject_name}_torsion_scaled.osim"
    else:
        final_osim_path = rf"C:\Git\isbs2024\Data\Scaled_models\{subject_name}_scaled.osim"

    default_markerset = model_with_generic_markerset.replace('.osim','_markerset.xml')

    # add the markerset to the final osim file
    export_markerset_osim(model_with_generic_markerset, default_markerset, [])
    add_markerset_to_osim(final_osim_path, final_osim_path, default_markerset)

    similar_markers, dif_markers = compare_markerset_osim(alex_model_complex, model_with_generic_markerset)
    print('similar_markers')
    print(similar_markers)
    print('dif_markers')
    print(dif_markers) 

    # add the markerset to the final osim file
    original_markerset_path = original_osim_path.replace('.osim', '_markerset.xml')
    export_markerset_osim(original_osim_path, original_markerset_path,dif_markers)
    # add_markerset_to_osim(final_osim_path, final_osim_path, original_markerset_path)

    cs.print_terminal_spaced('Please check the markers in opensim GUI against origina model and adjust if necessary')
    cs.print_to_log_file('\n\n Model adjusted for subject: {} \n'.format(subject_name))

    # reodrer markers
    orders_markers = ['GLAB','RFHD','LFHD','C7','T12','STRN', # upper body
                'RACR','RUAOL','RUA2','RUA3','RCUBL','RCUBM','RLAOL','RLA2','RLA3','RWRU','RWRR', # right arm
                'LACR','LUAOL','LUA2','LUA3','LCUBL','LCUBM','LLAOL','LLA2','LLA3','LWRU','LWRR', # left arm
                'RASI', 'LASI', 'RPSI', 'LPSI', 'SACROL', 'SACR2', 'SACR3', # pelvis
                'RTHOL', 'RTH2','RTH3','RKNEL', 'RKNEM', 'RSHAOL', 'RSHA2', 'RSHA3','RMALL', 'RMALM','RHEE','RM5','RTOE',# right leg
                'LTHOL', 'LTH2','LTH3','LKNEL', 'LKNEM', 'LSHAOL', 'LSHA2', 'LSHA3','LMALL', 'LMALM','LHEE','LM5','LTOE' # left leg
                ]                
    




     




# END