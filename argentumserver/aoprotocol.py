# -*- coding: utf-8 -*-

"""
    AONX Server - Pequeño servidor de Argentum Online.
    Copyright (C) 2011 Alejandro Santos <alejolp@alejolp.com.ar>

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

import sys, os, datetime

# Private Enum ServerPacketID

serverPacketsStr = r"""    Logged                  ' LOGGED
    RemoveDialogs           ' QTDL
    RemoveCharDialog        ' QDL
    NavigateToggle          ' NAVEG
    Disconnect              ' FINOK
    CommerceEnd             ' FINCOMOK
    BankEnd                 ' FINBANOK
    CommerceInit            ' INITCOM
    BankInit                ' INITBANCO
    UserCommerceInit        ' INITCOMUSU
    UserCommerceEnd         ' FINCOMUSUOK
    UserOfferConfirm
    CommerceChat
    ShowBlacksmithForm      ' SFH
    ShowCarpenterForm       ' SFC
    UpdateSta               ' ASS
    UpdateMana              ' ASM
    UpdateHP                ' ASH
    UpdateGold              ' ASG
    UpdateBankGold
    UpdateExp               ' ASE
    ChangeMap               ' CM
    PosUpdate               ' PU
    ChatOverHead            ' ||
    ConsoleMsg              ' || - Beware!! its the same as above, but it was properly splitted
    GuildChat               ' |+
    ShowMessageBox          ' !!
    UserIndexInServer       ' IU
    UserCharIndexInServer   ' IP
    CharacterCreate         ' CC
    CharacterRemove         ' BP
    CharacterChangeNick
    CharacterMove           ' MP, +, * and _ '
    ForceCharMove
    CharacterChange         ' CP
    ObjectCreate            ' HO
    ObjectDelete            ' BO
    BlockPosition           ' BQ
    PlayMidi                ' TM
    PlayWave                ' TW
    guildList               ' GL
    AreaChanged             ' CA
    PauseToggle             ' BKW
    RainToggle              ' LLU
    CreateFX                ' CFX
    UpdateUserStats         ' EST
    WorkRequestTarget       ' T01
    ChangeInventorySlot     ' CSI
    ChangeBankSlot          ' SBO
    ChangeSpellSlot         ' SHS
    Atributes               ' ATR
    BlacksmithWeapons       ' LAH
    BlacksmithArmors        ' LAR
    CarpenterObjects        ' OBR
    RestOK                  ' DOK
    ErrorMsg                ' ERR
    Blind                   ' CEGU
    Dumb                    ' DUMB
    ShowSignal              ' MCAR
    ChangeNPCInventorySlot  ' NPCI
    UpdateHungerAndThirst   ' EHYS
    Fame                    ' FAMA
    MiniStats               ' MEST
    LevelUp                 ' SUNI
    AddForumMsg             ' FMSG
    ShowForumForm           ' MFOR
    SetInvisible            ' NOVER
    DiceRoll                ' DADOS
    MeditateToggle          ' MEDOK
    BlindNoMore             ' NSEGUE
    DumbNoMore              ' NESTUP
    SendSkills              ' SKILLS
    TrainerCreatureList     ' LSTCRI
    guildNews               ' GUILDNE
    OfferDetails            ' PEACEDE & ALLIEDE
    AlianceProposalsList    ' ALLIEPR
    PeaceProposalsList      ' PEACEPR
    CharacterInfo           ' CHRINFO
    GuildLeaderInfo         ' LEADERI
    GuildMemberInfo
    GuildDetails            ' CLANDET
    ShowGuildFundationForm  ' SHOWFUN
    ParalizeOK              ' PARADOK
    ShowUserRequest         ' PETICIO
    TradeOK                 ' TRANSOK
    BankOK                  ' BANCOOK
    ChangeUserTradeSlot     ' COMUSUINV
    SendNight               ' NOC
    Pong
    UpdateTagAndStatus
    SpawnList               ' SPL
    ShowSOSForm             ' MSOS
    ShowMOTDEditionForm     ' ZMOTD
    ShowGMPanelForm         ' ABPANEL
    UserNameList            ' LISTUSU
    ShowGuildAlign
    ShowPartyForm
    UpdateStrenghtAndDexterity
    UpdateStrenght
    UpdateDexterity
    AddSlots
    MultiMessage
    StopWorking
    CancelOfferItem"""

# Private Enum ClientPacketID

clientPacketsStr = r"""    LoginExistingChar       'OLOGIN
    ThrowDices              'TIRDAD
    LoginNewChar            'NLOGIN
    Talk                    ';
    Yell                    '-
    Whisper                 '\
    Walk                    'M
    RequestPositionUpdate   'RPU
    Attack                  'AT
    PickUp                  'AG
    SafeToggle              '/SEG & SEG  (SEG's behaviour has to be coded in the client)
    ResuscitationSafeToggle
    RequestGuildLeaderInfo  'GLINFO
    RequestAtributes        'ATR
    RequestFame             'FAMA
    RequestSkills           'ESKI
    RequestMiniStats        'FEST
    CommerceEnd             'FINCOM
    UserCommerceEnd         'FINCOMUSU
    UserCommerceConfirm
    CommerceChat
    BankEnd                 'FINBAN
    UserCommerceOk          'COMUSUOK
    UserCommerceReject      'COMUSUNO
    Drop                    'TI
    CastSpell               'LH
    LeftClick               'LC
    DoubleClick             'RC
    Work                    'UK
    UseSpellMacro           'UMH
    UseItem                 'USA
    CraftBlacksmith         'CNS
    CraftCarpenter          'CNC
    WorkLeftClick           'WLC
    CreateNewGuild          'CIG
    SpellInfo               'INFS
    EquipItem               'EQUI
    ChangeHeading           'CHEA
    ModifySkills            'SKSE
    Train                   'ENTR
    CommerceBuy             'COMP
    BankExtractItem         'RETI
    CommerceSell            'VEND
    BankDeposit             'DEPO
    ForumPost               'DEMSG
    MoveSpell               'DESPHE
    MoveBank
    ClanCodexUpdate         'DESCOD
    UserCommerceOffer       'OFRECER
    GuildAcceptPeace        'ACEPPEAT
    GuildRejectAlliance     'RECPALIA
    GuildRejectPeace        'RECPPEAT
    GuildAcceptAlliance     'ACEPALIA
    GuildOfferPeace         'PEACEOFF
    GuildOfferAlliance      'ALLIEOFF
    GuildAllianceDetails    'ALLIEDET
    GuildPeaceDetails       'PEACEDET
    GuildRequestJoinerInfo  'ENVCOMEN
    GuildAlliancePropList   'ENVALPRO
    GuildPeacePropList      'ENVPROPP
    GuildDeclareWar         'DECGUERR
    GuildNewWebsite         'NEWWEBSI
    GuildAcceptNewMember    'ACEPTARI
    GuildRejectNewMember    'RECHAZAR
    GuildKickMember         'ECHARCLA
    GuildUpdateNews         'ACTGNEWS
    GuildMemberInfo         '1HRINFO<
    GuildOpenElections      'ABREELEC
    GuildRequestMembership  'SOLICITUD
    GuildRequestDetails     'CLANDETAILS
    Online                  '/ONLINE
    Quit                    '/SALIR
    GuildLeave              '/SALIRCLAN
    RequestAccountState     '/BALANCE
    PetStand                '/QUIETO
    PetFollow               '/ACOMPAÑAR
    ReleasePet              '/LIBERAR
    TrainList               '/ENTRENAR
    Rest                    '/DESCANSAR
    Meditate                '/MEDITAR
    Resucitate              '/RESUCITAR
    Heal                    '/CURAR
    Help                    '/AYUDA
    RequestStats            '/EST
    CommerceStart           '/COMERCIAR
    BankStart               '/BOVEDA
    Enlist                  '/ENLISTAR
    Information             '/INFORMACION
    Reward                  '/RECOMPENSA
    RequestMOTD             '/MOTD
    UpTime                  '/UPTIME
    PartyLeave              '/SALIRPARTY
    PartyCreate             '/CREARPARTY
    PartyJoin               '/PARTY
    Inquiry                 '/ENCUESTA ( with no params )
    GuildMessage            '/CMSG
    PartyMessage            '/PMSG
    CentinelReport          '/CENTINELA
    GuildOnline             '/ONLINECLAN
    PartyOnline             '/ONLINEPARTY
    CouncilMessage          '/BMSG
    RoleMasterRequest       '/ROL
    GMRequest               '/GM
    bugReport               '/_BUG
    ChangeDescription       '/DESC
    GuildVote               '/VOTO
    Punishments             '/PENAS
    ChangePassword          '/CONTRASEÑA
    Gamble                  '/APOSTAR
    InquiryVote             '/ENCUESTA ( with parameters )
    LeaveFaction            '/RETIRAR ( with no arguments )
    BankExtractGold         '/RETIRAR ( with arguments )
    BankDepositGold         '/DEPOSITAR
    Denounce                '/DENUNCIAR
    GuildFundate            '/FUNDARCLAN
    GuildFundation
    PartyKick               '/ECHARPARTY
    PartySetLeader          '/PARTYLIDER
    PartyAcceptMember       '/ACCEPTPARTY
    Ping                    '/PING
    RequestPartyForm
    ItemUpgrade
    GMCommands
    InitCrafting
    Home
    ShowGuildNews
    ShareNpc                '/COMPARTIR
    StopSharingNpc
    Consultation"""

def makePacketList(s):
    """Genera la lista de paquetes a partir del gran string anterior"""

    # Toma la primer palabra de cada linea y la numera.

    return dict([(x.strip().split(None, 1)[0], a) \
        for a, x in enumerate(s.split('\n'))])

def generatePacketsHandler(packets, f):
    """Generador de codigo para los handlers de los paquetes del cliente"""
    p = sorted(packets.items(), key=lambda x: x[1])

    for x in p:
        f.write("""
    @CheckLogged
    def handleCmd%(PacketName)s(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME
""" % {'PacketName': x[0]})

def generatePacketsSender(packets, f, listName='serverPackets'):
    """Generador de codigo para los senders de los paquetes del servidor"""

    p = sorted(packets.items(), key=lambda x: x[1])

    for x in p:
        f.write("""
    def send%(PacketName)s(self):
        self.buf.writeInt8(%(PacketsListName)s['%(PacketName)s'])
        raise CriticalDecoderException('Not Implemented')
        # FIXME

        self.prot.flushOutBuf()
""" % {'PacketName': x[0], 'PacketsListName': listName})

def generatePackets():
    with open('paquetes-cliente.txt', 'wb') as f:
        generatePacketsHandler(clientPackets, f)

    with open('paquetes-servidor.txt', 'wb') as f:
        generatePacketsSender(serverPackets, f)

def generatePacketsJava(basePath = None):
    if basePath is None:
        basePath = sys.argv[1]

    fecha = datetime.datetime.now().isoformat(' ')

    p = sorted(clientPackets.items(), key=lambda x: x[1])
    p2 = sorted(serverPackets.items(), key=lambda x: x[1])

    with open(os.path.join(basePath, 'ClientPacketsFactory.java'), 'wb') as f:
        f.write("""/**
 * Automatically generated code (%(Fecha)s).
 */

package com.ao.net;

public class ClientPacketsFactory {\n""" % {'Fecha': fecha})
        for x in p:
            f.write("""    public static final int %(PacketName)s_ID = %(PacketID)s;\n""" % {'PacketName': x[0], 'PacketID': str(x[1])})
        f.write("""    
    public static ClientPacket CreatePacket(int packetNum, Object player) {
    	switch (packetNum) {
""")

        for x in p:
            f.write("        case %(PacketName)s_ID: return new com.ao.net.client.%(PacketName)s(player); \n" % {'PacketName': x[0], 'Fecha': fecha})
        f.write("""        }
        
        throw new RuntimeException("Ivalid Packet ID");
        // return null;
    }
}
""")

    with open(os.path.join(basePath, 'ServerPacketsFactory.java'), 'wb') as f:
        f.write("""/**
 * Automatically generated code (%(Fecha)s).
 */

package com.ao.net;

public class ServerPacketsFactory {\n""" % {'Fecha': fecha})
        for x in p2:
            f.write("""    public static final int %(PacketName)s_ID = %(PacketID)s;\n""" % {'PacketName': x[0], 'PacketID': str(x[1])})
        f.write("}\n")

    if not os.path.isdir(os.path.join(basePath, 'client')):
        os.makedirs(os.path.join(basePath, 'client'))

    if not os.path.isdir(os.path.join(basePath, 'server')):
        os.makedirs(os.path.join(basePath, 'server'))

    for x in p:
        with open(os.path.join(basePath, 'client', x[0] + '.java'), 'wb') as f:
            f.write("""/**
 * Automatically generated code (%(Fecha)s).
 */

package com.ao.net.client;

import com.ao.net.ChannelBuffer2;
import com.ao.net.ClientPacket;
import com.ao.net.ClientPacketsFactory;

public class %(PacketName)s extends ClientPacket {
    public %(PacketName)s(Object player) {
        super(ClientPacketsFactory.%(PacketName)s_ID, player);
    }

    @Override
    public void decode(ChannelBuffer2 buf) {
        throw new RuntimeException("Not Implemented"); // FIXME
    }

    @Override
    public void handle() {
        throw new RuntimeException("Not Implemented"); // FIXME
    }
}
""" % {'PacketName': x[0], 'Fecha': fecha})

    for x in p2:
        with open(os.path.join(basePath, 'server', x[0] + '.java'), 'wb') as f:
            f.write("""/**
 * Automatically generated code (%(Fecha)s).
 */

package com.ao.net.server;

import com.ao.net.ChannelBuffer2;
import com.ao.net.ServerPacket;
import com.ao.net.ServerPacketsFactory;

public class %(PacketName)s extends ServerPacket {

	public %(PacketName)s() {
		super(ServerPacketsFactory.%(PacketName)s_ID);
	}

	@Override
	public void encode(ChannelBuffer2 buf) {
		// buf.writeByte(getPacketNum());
		throw new RuntimeException("Not Implemented"); // FIXME
	}
}
""" % {'PacketName': x[0], 'Fecha': fecha})

# Dado un nombre de paquete (Logged, etc.) devuelve el PacketID.
serverPackets = makePacketList(serverPacketsStr)
clientPackets = makePacketList(clientPacketsStr)

# Dado un PacketID (0, 1, etc.) devuelve el nombre del paquete.
serverPacketsFlip = dict([(b, a) for a, b in serverPackets.items()])
clientPacketsFlip = dict([(b, a) for a, b in clientPackets.items()])

lastServerPacketID = max(serverPackets.values())
lastClientPacketID = max(clientPackets.values())

__all__ = ['serverPackets', 'clientPackets']

if __name__ == '__main__':
    generatePacketsJava()

