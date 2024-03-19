import pandas

pos_data = pd.DataFrame([(x_coord, y_coord, z_coord)], columns=['nx', 'ny', 'nz'])
pos_data.to_csv('C:/Users/3Dstation3/Desktop/PosData.txt')
print(pos_data)