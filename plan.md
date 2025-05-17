``` 
y
|
+-- x
```

DODATKI
 CACHE MINY ZEBY LEPZY PATHFINDING
 FOCUS 1 CZOLG najpierw light potem heavy, potem dodac odleglosc?
 W ATAKU UNIKANIE ENEMY LUFY IF OUT OF AMMO


sth:
    determine self state


## ms:
- [x] my_cords
- [x] teammates_cords
- [x] teammates_in_clear_line_of_sight
- [x] enemy_in_clear_line_of_sight
- [ ] penalty dla lasera przeciwnika
- [ ] poruszanie si 

## mrokcin:

### Szukanie zone:
- [x] _find_zone
- [x] _get_zone_coordinates DO TESTA
  - zone tiles:  [(9, 12), (10, 12), (11, 12), (12, 12), (9, 13), (10, 13), (11, 13), (12, 13), (10, 14), (11, 14), (12, 14), (9, 15), (10, 15), (12, 15)]
- [X] _goto_zone
  - Funkcja poruszająca się do losowego tile strefy
- [x] capturing kiedy jesteśmy w zone
- [ ] poruszanie się do przeciwnika